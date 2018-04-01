from django.db import models
from django.db.utils import OperationalError
from operator import itemgetter
import datetime
from django.contrib.auth.hashers import make_password
from django.utils.text import slugify
from django.core.paginator import Paginator
import logging
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


def correct_dates_to_due_day(days):
    return correct_dates_to_weekday(days, Config.objects.first().date_due)


def correct_dates_to_weekday(days, weekday):
    """Days is a date or list of timezone.date objects you want converted. 0 = Monday, 6 = Sunday"""
    if isinstance(days, list):
        corrected_days = []
        for day in days:
            if day:
                day += timezone.timedelta(days=weekday - day.weekday())
            corrected_days.append(day)
        return corrected_days
    elif isinstance(days, datetime.date):
        return days + timezone.timedelta(days=weekday - days.weekday())
    return None


class Config(models.Model):
    WEEKDAYS = ((0, 'Montag'), (1, 'Dienstag'), (2, 'Mittwoch'), (3, 'Donnerstag'), (4, 'Freitag'),
                (5, 'Samstag'), (6, 'Sonntag'))
    date_due = models.IntegerField(default=6, choices=WEEKDAYS)
    starts_days_before_due = models.IntegerField(default=1)
    ends_days_after_due = models.IntegerField(default=2)

    trust_in_users = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.__trust_in_users = self.trust_in_users
        self.__date_due = self.date_due

    def timedelta_before_due(self):
        return timezone.timedelta(days=self.starts_days_before_due)

    def timedelta_ends_after_due(self):
        return timezone.timedelta(days=self.ends_days_after_due)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.pk and Config.objects.count() != 0:
            return
        super().save(force_insert, force_update, using, update_fields)

        if self.__trust_in_users != self.trust_in_users:
            Cleaner.objects.reset_passwords()

        if self.__date_due != self.date_due:
            pass
            # TODO Change all Assignment dates and CleaningDate dates


def app_config():
    return Config.objects.first()


try:
    if Config.objects.count() == 0:
        Config.objects.create()
except OperationalError:
    pass


class Schedule(models.Model):
    class Meta:
        ordering = ('cleaners_per_date',)
    name = models.CharField(max_length=20, unique=True)
    slug = models.CharField(max_length=20, unique=True)

    CLEANERS_PER_DATE_CHOICES = ((1, 'Einen'), (2, 'Zwei'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Jede Woche'), (2, 'Gerade Wochen'), (3, 'Ungerade Wochen'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)
    tasks = models.CharField(max_length=200, null=True)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.__last_cleaners_per_date = self.cleaners_per_date
        self.__last_frequency = self.frequency

    def get_tasks(self):
        return self.tasks.split(",") if self.tasks else None

    def cleaners_assigned(self):
        return Cleaner.objects.filter(schedule_group__schedules=self)

    def get_active_assignments(self):
        """Returns Assignments for this Schedule that are active today or were have
        recently passed (if no Assignment is currently active) """
        starts_before = datetime.timedelta(days=app_config().starts_days_before_due)
        ends_after = datetime.timedelta(days=app_config().ends_days_after_due)
        today = timezone.datetime.today()
        return self.assignment_set.filter(date__range=(today - ends_after, today + starts_before))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.slug = slugify(self.name)
        super(Schedule, self).save(force_insert, force_update, using, update_fields)

        if self.cleaners_per_date != self.__last_cleaners_per_date or self.frequency != self.__last_frequency:
            all_duty_dates = list(self.cleaningday_set.values_list('date', flat=True))
            self.cleaningday_set.all().delete()
            self.assignment_set.all().delete()
            for date in all_duty_dates:
                self.assign_cleaning_duty(date)

    def deployment_ratios(self, for_date, cleaners=None):
        """Returns <number of duties a cleaner cleans in>/<total number of duties> on date for_date.
        Ratios are calculated over a time window that stretches into the past and the future, ignoring
        duties that have no cleaners assigned. If you wish to know only the ratio of a select number
        of cleaners, pass them in a list in the cleaners argument. Otherwise all ratios will be returned."""
        ratios = []

        members_on_date = Cleaner.objects.filter(schedule_group__schedules=self,
                                                 moved_out__gte=for_date, moved_in__lte=for_date)

        if cleaners:
            iterate_over = cleaners
        else:
            iterate_over = members_on_date

        if iterate_over:
            proportion__cleaners_assigned_per_week = self.cleaners_per_date / len(members_on_date)

            for cleaner in iterate_over:
                all_assignments = self.assignment_set.filter(date__range=(cleaner.moved_in, cleaner.moved_out))

                if all_assignments.exists():
                    proportion__self_assigned = all_assignments.filter(cleaner=cleaner).count() / all_assignments.count()
                    ratios.append([cleaner,
                                   proportion__self_assigned / proportion__cleaners_assigned_per_week])
                else:
                    ratios.append([cleaner, 0])
            return sorted(ratios, key=itemgetter(1), reverse=False)
        else:
            return []

    def defined_on_date(self, date):
        return self.frequency == 1 or self.frequency == 2 and date.isocalendar()[1] % 2 == 0 or \
               self.frequency == 3 and date.isocalendar()[1] % 2 == 1

    def new_cleaning_duties(self, date1, date2, clear_existing=True):
        """Generates new cleaning duties between date1 and date2."""
        start_date = min(date1, date2)
        end_date = max(date1, date2)
        one_week = timezone.timedelta(days=7)

        if clear_existing:
            self.assignment_set.filter(date__range=(start_date, end_date)).delete()

        date_iterator = start_date
        while date_iterator <= end_date:
            if clear_existing or not clear_existing and \
                    self.assignment_set.filter(date=date_iterator).count() < self.cleaners_per_date:
                self.assign_cleaning_duty(date_iterator)
            date_iterator += one_week

    def assign_cleaning_duty(self, date):
        """Generates a new Duty and assigns Cleaners to it.
        If the Schedule is not defined on date (see defined_on_date()), then this function fails silently."""

        if self.defined_on_date(date):
            cleaning_day, was_created = self.cleaningday_set.get_or_create(date=date)

            ratios = self.deployment_ratios(date)
            if logging.getLogger(__name__).getEffectiveLevel() >= logging.DEBUG:
                logging.debug('------------- CREATING NEW CLEANING DUTY FOR {} on the {} -------------'.format(self.name, date))
                logging_text = "All cleaners' ratios: "
                for cleaner, ratio in ratios:
                    logging_text += "{}:{}".format(cleaner.name, round(ratio, 3)) + "  "
                logging.debug(logging_text)

            last_resort_cleaner = None
            if ratios:
                for i in range(min(self.cleaners_per_date-self.assignment_set.filter(date=date).count(), len(ratios))):
                    for cleaner, ratio in ratios:
                        if not self.assignment_set.filter(date=date, cleaner=cleaner).exists() and \
                                cleaner not in cleaning_day.excluded.all():
                            if cleaner.assignment_set.filter(date=date).count() == 0:
                                self.assignment_set.create(date=date, cleaner=cleaner)
                                logging.debug("          {} inserted!".format(cleaner.name))
                                break
                            elif not last_resort_cleaner and cleaner.assignment_set.filter(date=date).count() == 1:
                                last_resort_cleaner = cleaner
                            logging.debug("{} is not free.".format(cleaner.name))
                    else:
                        if last_resort_cleaner:
                            logging.debug("Nobody has 0 duties on date so we choose {}".format(last_resort_cleaner))
                            self.assignment_set.create(date=date, cleaner=last_resort_cleaner)
                        else:
                            logging.debug("NOBODY HAS 1 DUTY ON DATE! We choose {}".format(ratios[0][0]))
                            self.assignment_set.create(date=date, cleaner=ratios[0][0])
            else:
                return None

            logging.debug("")
        else:
            return None


class ScheduleGroup(models.Model):
    class Meta:
        ordering = ("name", )
    name = models.CharField(max_length=30, unique=True)
    schedules = models.ManyToManyField(Schedule)

    def __str__(self):
        return self.name


class CleanerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(moved_out__gte=timezone.now().date())


class CleanerManager(models.Manager):
    def get_queryset(self):
        return CleanerQuerySet(self.model, using=self._db)

    def reset_passwords(self):
        if Config.objects.first().trust_in_users:
            for cleaner in self.all():
                cleaner.user.set_password(cleaner.slug)
        else:
            pass
            # TODO Send out email/Slack messages for password setting


class Cleaner(models.Model):
    class Meta:
        ordering = ('name',)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=10, unique=True)
    moved_in = models.DateField()
    moved_out = models.DateField()
    time_zone = models.CharField(max_length=30, default="Europe/Berlin")
    slack_id = models.CharField(max_length=10, null=True)
    schedule_group = models.ForeignKey(ScheduleGroup, on_delete=models.SET_NULL, null=True)

    objects = CleanerManager.from_queryset(CleanerQuerySet)()

    def __init__(self, *args, **kwargs):
        super(Cleaner, self).__init__(*args, **kwargs)
        self.__last_moved_in = self.moved_in
        self.__last_moved_out = self.moved_out
        self.__last_group = self.schedule_group

    def __str__(self):
        return self.name

    def rejected_dutyswitch_requests(self):
        return DutySwitch.objects.filter(source_assignment__cleaner=self, status=2)

    def dutyswitch_requests_received(self):
        return DutySwitch.objects.filter(selected_assignment__cleaner=self)

    def pending_dutyswitch_requests(self):
        return DutySwitch.objects.filter(source_assignment__cleaner=self, status=1)

    def has_pending_requests(self):
        return self.pending_dutyswitch_requests().exists() or self.dutyswitch_requests_received().exists() or \
               self.rejected_dutyswitch_requests().exists()

    def nr_assignments_on_day(self, date):
        return self.assignment_set.filter(date=date).count()

    def delete(self, using=None, keep_parents=False):
        if self.schedule_group:
            group = self.schedule_group
            self.schedule_group = None
            self.save()
            for schedule in group.schedules.all():
                schedule.new_cleaning_duties(self.moved_in, self.moved_out)
        self.user.delete()
        super().delete(using, keep_parents)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)

        if not self.user:
            new_password = self.slug if Config.objects.first().trust_in_users else make_password(None)
            self.user = User.objects.create(username=self.slug, password=new_password)
        elif self.user.username != self.slug:
            self.user.username = self.slug
            if Config.objects.first().trust_in_users:
                self.user.set_password(self.slug)
            self.user.save()

        super().save(force_insert, force_update, using, update_fields)

        if self.moved_out != self.__last_moved_out:
            prev_last_duty, new_last_duty = correct_dates_to_due_day([self.__last_moved_out, self.moved_out])
            if prev_last_duty and prev_last_duty != new_last_duty:
                for schedule in self.schedule_group.schedules.all():
                    schedule.new_cleaning_duties(prev_last_duty, new_last_duty, True)

        if self.moved_in != self.__last_moved_in:
            prev_first_duty, new_first_duty = correct_dates_to_due_day([self.__last_moved_in, self.moved_in])
            if prev_first_duty and prev_first_duty != new_first_duty:
                for schedule in self.schedule_group.schedules.all():
                    schedule.new_cleaning_duties(prev_first_duty, new_first_duty, True)

        if self.schedule_group and self.schedule_group != self.__last_group:
            if self.__last_group:
                schedules_to_reassign = self.schedule_group.schedules.intersection(self.__last_group.schedules)
            else:
                schedules_to_reassign = self.schedule_group.schedules
            for schedule in schedules_to_reassign.all():
                schedule.new_cleaning_duties(self.moved_in, self.moved_out)


# def group_cleaners_changed(instance, action, pk_set, **kwargs):
#     if action == 'post_add' or action == 'post_remove':
#         dates_to_delete = []
#         one_week = timezone.timedelta(days=7)
#         for cleaner_pk in pk_set:
#             cleaner = Cleaner.objects.get(pk=cleaner_pk)
#             first_duty, last_duty = correct_dates_to_due_day([min(cleaner.moved_in, timezone.date.today()),
#                                                               cleaner.moved_out])
#             date_iterator = first_duty
#             while date_iterator <= last_duty:
#                 if date_iterator not in dates_to_delete:
#                     dates_to_delete.append(date_iterator)
#                 date_iterator += one_week
#
#         for schedule in Schedule.objects.filter(schedule_group=instance):
#             dates_to_redistribute = []
#             for date in dates_to_delete:
#                 duty = schedule.duties.filter(date=date)
#                 if duty.exists():
#                     duty.delete()
#                     dates_to_redistribute.append(date)
#             for date in dates_to_redistribute:
#                 schedule.assign_cleaning_duty(date)


# m2m_changed.connect(group_cleaners_changed, sender=ScheduleGroup.cleaners.through)

class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=timezone.now().date())
    date = models.DateField()
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    class Meta:
        ordering = ('-date',)

    def __str__(self):
        return self.schedule.name + ": " + self.cleaner.name + " on the " + str(self.date)

    def cleaners_on_date_for_schedule(self):
        return Cleaner.objects.filter(assignment__schedule=self.schedule,
                                      assignment__date=self.date)

    def possible_start_date(self):
        return self.date - timezone.timedelta(days=app_config().starts_days_before_due)

    def cleaning_buddies(self):
        return self.cleaners_on_date_for_schedule().exclude(pk=self.cleaner.pk)

    def tasks_cleaned(self):
        return Task.objects.filter(cleaned_by=self)

    def cleaning_day(self):
        try:
            return self.schedule.cleaningday_set.get(date=self.date)
        except CleaningDay.DoesNotExist:
            return None


class Task(models.Model):
    name = models.CharField(max_length=20)
    cleaned_by = models.ForeignKey(Assignment, null=True, on_delete=models.CASCADE)


    def __str__(self):
        return str(self.name)


class CleaningDay(models.Model):
    class Meta:
        ordering = ('-date',)
        unique_together = ('date', 'schedule')
    tasks = models.ManyToManyField(Task)
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.schedule)+"-"+str(self.date)

    def initiate_tasks(self):
        schedule = self.schedule
        task_list = schedule.get_tasks()
        if task_list:
            for task in task_list:
                self.tasks.create(name=task)

    def delete(self, using=None, keep_parents=False):
        self.tasks.all().delete()
        super().delete(using, keep_parents)


class DutySwitch(models.Model):
    class Meta:
        ordering = ('created',)
    created = models.DateField(auto_now_add=timezone.now().date())

    source_assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="source")
    selected_assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True, related_name="selected")
    destinations = models.ManyToManyField(Assignment)

    STATES = ((0, 'Waiting on source choice'), (1, 'Waiting on approval for selected'), (2, 'Selected was rejected'))
    status = models.IntegerField(choices=STATES, default=0)
    # DutySwitch object gets created in statue 0 as Cleaner needs to select a desired Duty destination.
    # When the desired Duty is selected the status is set to 1 because we need approval
    # from the destination to commence switching.
    # If the destination denies approval, status is set to 2 because the source needs to select a new
    # destination. The cycle begins from the start

    def __str__(self):
        return "Source assignment: "+str(self.source_assignment)

    def filtered_destinations(self):
        destinations = self.destinations.exclude(pk=self.source_assignment.pk)
        if self.selected_assignment:
            destinations = destinations.exclude(pk=self.selected_assignment.pk)
        return destinations

    def set_selected(self, assignment):
        self.selected_assignment = assignment
        self.status = 1
        self.save()

    def selected_was_accepted(self):
        try:
            cleaning_day = self.source_assignment.cleaning_day()
        except CleaningDay.DoesNotExist:
            return
        cleaning_day.excluded.add(self.source_assignment.cleaner)

        temp_date = self.source_assignment.date
        self.source_assignment.date = self.selected_assignment.date
        self.source_assignment.save()
        self.selected_assignment.date = temp_date
        self.selected_assignment.save()

        for destination in list(DutySwitch.objects.filter(selected_assignment=self.source_assignment)) + \
                list(DutySwitch.objects.filter(selected_assignment=self.selected_assignment)):
            destination.selected_was_rejected()

        for destination in list(DutySwitch.objects.filter(source_assignment=self.source_assignment)) + \
                list(DutySwitch.objects.filter(source_assignment=self.selected_assignment)):
            destination.delete()

        self.delete()

    def selected_was_cancelled(self):
        self.selected_assignment = None
        self.status = 0
        self.save()

    def selected_was_rejected(self):
        self.destinations.remove(self.selected_assignment)
        self.selected_assignment = None
        self.status = 2
        self.save()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        if not self.destinations.all():
            schedule = self.source_assignment.schedule

            possible_cleaners = Cleaner.objects.filter(
                schedule_group__schedules=schedule).exclude(
                pk=self.source_assignment.cleaner.pk)

            cleaning_day = self.source_assignment.cleaning_day()

            if cleaning_day:
                possible_cleaners = possible_cleaners.exclude(slug__in=cleaning_day.excluded.all())

            ratios = schedule.deployment_ratios(self.source_assignment.date, list(possible_cleaners))

            logging.debug("------------ Looking for replacement cleaners -----------")

            one_duty_cleaners = []
            source_is_already_assigned = []

            for cleaner, ratio in ratios:
                logging.debug(
                    "{}:  Duties today:{}".
                        format(cleaner.name,
                               cleaner.nr_assignments_on_day(self.source_assignment.date)))

                nr_assignments_on_day = cleaner.nr_assignments_on_day(self.source_assignment.date)
                assignments_in_future = schedule.assignment_set.filter(
                    cleaner=cleaner, date__gt=timezone.now().date())

                if nr_assignments_on_day == 0:
                    for assignment in assignments_in_future:
                        source_assignments_on_day = self.source_assignment.cleaner.nr_assignments_on_day(assignment.date)
                        if source_assignments_on_day == 0:
                            self.destinations.add(assignment)
                        else:
                            source_is_already_assigned.append(assignment)

                elif nr_assignments_on_day == 1:
                    for assignment in assignments_in_future:
                        one_duty_cleaners.append(assignment)

            if not self.destinations.all():
                if source_is_already_assigned:
                    for assignment in source_is_already_assigned:
                        self.destinations.add(assignment)
                else:
                    for assignment in one_duty_cleaners:
                        self.destinations.add(assignment)

