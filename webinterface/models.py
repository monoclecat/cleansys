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


class ScheduleQuerySet(models.QuerySet):
    def active(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


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

    disabled = models.BooleanField(default=False)

    objects = ScheduleQuerySet.as_manager()

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.__last_cleaners_per_date = self.cleaners_per_date
        self.__last_frequency = self.frequency

    def get_tasks(self):
        possibly_with_leading_or_trailing_spaces = self.tasks.split(",") if self.tasks else None
        spaceless = []
        for task in possibly_with_leading_or_trailing_spaces:
            if len(task) > 1 and task[0] == " ":
                task = task[1:]
            if len(task) > 1 and task[-1] == " ":
                task = task[:-1]
            spaceless.append(task)
        return spaceless

    def affiliations(self):
        return Affiliation.objects.filter(group__schedules=self)

    def affiliations_active_on_date(self, date):
        return self.affiliations().filter(beginning__lte=date, end__gt=date)

    def get_active_assignments(self):
        """Returns Assignments for this Schedule that are active today or were have
        recently passed (if no Assignment is currently active) """
        starts_before = datetime.timedelta(days=app_config().starts_days_before_due)
        ends_after = datetime.timedelta(days=app_config().ends_days_after_due)
        today = timezone.datetime.today()
        return self.assignment_set.filter(cleaning_day__date__range=(today - ends_after, today + starts_before))

    def get_current_cleaning_day(self):
        """Returns Assignments for this Schedule that are active today or were have
        recently passed (if no Assignment is currently active) """
        starts_before = datetime.timedelta(days=app_config().starts_days_before_due)
        ends_after = datetime.timedelta(days=app_config().ends_days_after_due)
        today = timezone.datetime.today()
        return self.cleaningday_set.get(date__range=(today - ends_after, today + starts_before))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.slug = slugify(self.name)
        super(Schedule, self).save(force_insert, force_update, using, update_fields)

        if self.cleaners_per_date != self.__last_cleaners_per_date or self.frequency != self.__last_frequency:
            all_duty_dates = list(self.cleaningday_set.values_list('date', flat=True))
            self.cleaningday_set.all().delete()
            self.assignment_set.all().delete()
            for date in all_duty_dates:
                self.create_assignment(date)

    def deployment_ratios(self, date):
        ratios = []

        active_affiliations = self.affiliations_active_on_date(date)

        if active_affiliations.exists():
            for active_affiliation in active_affiliations:
                cleaner = active_affiliation.cleaner
                assignments_during_affiliations = Assignment.objects.none()

                for affiliation in cleaner.affiliation_set.all():
                    assignments_during_affiliations |= self.assignment_set.filter(
                        cleaning_day__date__range=(affiliation.beginning, affiliation.end))

                if assignments_during_affiliations.exists():
                    proportion__self_assigned = assignments_during_affiliations.filter(cleaner=cleaner).count() \
                        / assignments_during_affiliations.count()

                    ratios.append([cleaner, proportion__self_assigned])
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
            self.cleaningday_set.filter(date__range=(start_date, end_date)).delete()

        date_iterator = start_date
        while date_iterator <= end_date:
            while self.create_assignment(date_iterator):
                pass
            date_iterator += one_week

    def create_assignment(self, date):
        """Generates a new Duty and assigns Cleaners to it.
        If the Schedule is not defined on date (see defined_on_date()), then this function fails silently."""

        if self.defined_on_date(date):
            cleaning_day, was_created = self.cleaningday_set.get_or_create(date=correct_dates_to_due_day(date))

            ratios = self.deployment_ratios(date)

            if logging.getLogger(__name__).getEffectiveLevel() >= logging.DEBUG:
                logging.debug('------------- CREATING NEW CLEANING DUTY FOR {} on the {} -------------'.format(self.name, date))
                logging_text = "All cleaners' ratios: "
                for cleaner, ratio in ratios:
                    logging_text += "{}: {}".format(cleaner.name, round(ratio, 3)) + "  "
                logging.debug(logging_text)

            if ratios and cleaning_day.assignment_set.count() < self.cleaners_per_date:
                for cleaner, ratio in ratios:
                    if cleaner.is_eligible_for_date(date) and cleaner not in cleaning_day.excluded.all():
                        logging.debug("   {} inserted!".format(cleaner.name))
                        return self.assignment_set.create(cleaner=cleaner, cleaning_day=cleaning_day)
                    else:
                        logging.debug("   {} already has {} duties today.".format(
                            cleaner.name, cleaner.nr_assignments_on_day(date)))
                else:
                    logging.debug("   Cleaner's preferences result in no cleaner, we must choose {}".format(ratios[0][0]))
                    return self.assignment_set.create(cleaner=ratios[0][0], cleaning_day=cleaning_day)
            else:
                return False
        else:
            return False


class ScheduleGroupQuerySet(models.QuerySet):
    def active(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


class ScheduleGroup(models.Model):
    class Meta:
        ordering = ("name", )
    name = models.CharField(max_length=30, unique=True)
    schedules = models.ManyToManyField(Schedule)
    disabled = models.BooleanField(default=False)

    objects = ScheduleGroupQuerySet.as_manager()

    def __str__(self):
        return self.name


class CleanerQuerySet(models.QuerySet):
    # def active(self):
    #     return ???
    #
    # def inactive(self):
    #     return ???

    def no_slack_id(self):
        return self.filter(slack_id='')

    def has_slack_id(self):
        return self.exclude(slack_id='')


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

    time_zone = models.CharField(max_length=30, default="Europe/Berlin")
    slack_id = models.CharField(max_length=10, default='')

    PREFERENCE = ((1, 'Ich möchte immer nur einen Putzdienst auf einmal machen müssen.'),
                  (2, 'Ich möchte höchstens zwei Putzdienste auf einmal machen müssen.'),
                  (3, 'Mir ist es egal, wie viele Putzdienste ich auf einmal habe.'))
    preference = models.IntegerField(choices=PREFERENCE, default=2)

    objects = CleanerManager.from_queryset(CleanerQuerySet)()

    def __str__(self):
        return self.name

    def current_affiliation(self):
        current_affiliation_queryset = self.affiliation_set.filter(
            beginning__lt=timezone.now().date(), end__gte=timezone.now().date())
        if current_affiliation_queryset.exists():
            return current_affiliation_queryset.first()
        else:
            return None

    def is_active(self):
        return self.current_affiliation() is not None

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
        return self.assignment_set.filter(cleaning_day__date=date).count()

    def is_eligible_for_date(self, date):
        nr_assignments_on_day = self.nr_assignments_on_day(date)
        return nr_assignments_on_day == 0 or nr_assignments_on_day == 1 and self.preference == 2 \
            or self.preference == 3

    def delete(self, using=None, keep_parents=False):
        self.user.delete()
        super().delete(using, keep_parents)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)

        if not self.user:
            try:
                new_password = self.slug if Config.objects.first().trust_in_users else make_password(None)
            except AttributeError:
                logging.error("No Config object exists! Set password of user {} to unusable password.".format(self.name))
                new_password = make_password(None)
            self.user = User.objects.create(username=self.slug, password=new_password)
        elif self.user.username != self.slug:
            self.user.username = self.slug
            if Config.objects.first().trust_in_users:
                self.user.set_password(self.slug)
            self.user.save()

        super().save(force_insert, force_update, using, update_fields)

        # if self.moved_out != self.__last_moved_out:
        #     prev_last_duty, new_last_duty = correct_dates_to_due_day([self.__last_moved_out, self.moved_out])
        #     if prev_last_duty and prev_last_duty != new_last_duty:
        #         for schedule in self.schedule_group.schedules.all():
        #             schedule.new_cleaning_duties(prev_last_duty, new_last_duty, True)
        #
        # if self.moved_in != self.__last_moved_in:
        #     prev_first_duty, new_first_duty = correct_dates_to_due_day([self.__last_moved_in, self.moved_in])
        #     if prev_first_duty and prev_first_duty != new_first_duty:
        #         for schedule in self.schedule_group.schedules.all():
        #             schedule.new_cleaning_duties(prev_first_duty, new_first_duty, True)

        # if self.schedule_group and self.schedule_group != self.__last_group:
        #     if self.__last_group:
        #         schedules_to_reassign = self.schedule_group.schedules.all() | self.__last_group.schedules.all()
        #     else:
        #         schedules_to_reassign = self.schedule_group.schedules.all()
        #     for schedule in schedules_to_reassign:
        #         schedule.new_cleaning_duties(correct_dates_to_due_day(self.moved_in),
        #                                      correct_dates_to_due_day(self.moved_out))


class Affiliation(models.Model):
    class Meta:
        ordering=('-end',)
    # TODO Make sure affiliations for a cleaner do NOT overlap in time!
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    group = models.ForeignKey(ScheduleGroup, on_delete=models.CASCADE)

    beginning = models.DateField(null=True)
    end = models.DateField(default=datetime.date.max)

    def __str__(self):
        if self.group:
            return self.cleaner.name + " in " + self.group.name + " from " + str(self.beginning) + " to " + str(self.end)
        else:
            return self.cleaner.name + " moved out from " + str(self.beginning) + " to " + str(self.end)


class CleaningDay(models.Model):
    class Meta:
        ordering = ('-date',)
        unique_together = ('date', 'schedule')
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return "{}: {}".format(self.schedule.name, self.date.strftime('%d-%b-%Y'))

    def initiate_tasks(self):
        schedule = self.schedule
        task_list = schedule.get_tasks()
        if task_list:
            for task in task_list:
                self.task_set.create(name=task)

    def open_tasks(self):
        return self.task_set.filter(cleaned_by__isnull=True)

    def done_tasks(self):
        return self.task_set.filter(cleaned_by__isnull=False)

    def delete(self, using=None, keep_parents=False):
        self.task_set.all().delete()
        super().delete(using, keep_parents)


class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=timezone.now().date())
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    # TODO Why do we need a FK to schedule if we have one to CleaningDay?
    cleaning_day = models.ForeignKey(CleaningDay, on_delete=models.CASCADE)

    class Meta:
        ordering = ('cleaning_day__date',)

    def __str__(self):
        return "{}: {}, {} ".format(self.schedule.name, self.cleaner.name, self.cleaning_day.date.strftime('%d-%b-%Y'))

    def cleaners_on_date_for_schedule(self):
        return Cleaner.objects.filter(assignment__cleaning_day=self.cleaning_day)

    def possible_start_date(self):
        return self.cleaning_day.date - timezone.timedelta(days=app_config().starts_days_before_due)

    def cleaning_buddies(self):
        return self.cleaners_on_date_for_schedule().exclude(pk=self.cleaner.pk)

    def tasks_cleaned(self):
        return Task.objects.filter(cleaned_by=self)

    def is_up_for_switching(self):
        duty_switch = DutySwitch.objects.filter(source_assignment=self)
        if duty_switch.exists():
            return duty_switch.first()
        else:
            return False

    def finished_cleaning(self):
        if self.cleaning_day.task_set.all():
            return not self.cleaning_day.task_set.filter(cleaned_by__isnull=True).exists()
        else:
            return False


class Task(models.Model):
    name = models.CharField(max_length=20)
    cleaned_by = models.ForeignKey(Assignment, null=True, on_delete=models.CASCADE)
    cleaning_day = models.ForeignKey(CleaningDay, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


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
        if self.selected_assignment:
            return "Source: {} on {}  -  Selected: {} on {}  -  Status: {} ".\
                format(self.source_assignment.cleaner.name, self.source_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
                       self.selected_assignment.cleaner.name, self.selected_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
                       self.status)
        else:
            return "Source: {} on {}  -  Selected:            -  Status: {} ". \
                format(self.source_assignment.cleaner.name, self.source_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
                       self.status)

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
        cleaning_day = self.source_assignment.cleaning_day

        cleaning_day.excluded.add(self.source_assignment.cleaner)

        source_cleaning_day = self.source_assignment.cleaning_day
        self.source_assignment.cleaning_day = self.selected_assignment.cleaning_day
        self.source_assignment.save()
        self.selected_assignment.cleaning_day = source_cleaning_day
        self.selected_assignment.save()

        all_except_self = DutySwitch.objects.exclude(pk=self.pk)

        for destination in all_except_self.filter(selected_assignment=self.source_assignment) | \
                all_except_self.filter(selected_assignment=self.selected_assignment):
            destination.selected_was_rejected()

        for destination in all_except_self.filter(source_assignment=self.source_assignment) | \
                all_except_self.filter(source_assignment=self.selected_assignment):
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

    def look_for_destinations(self):
        schedule = self.source_assignment.schedule

        active_affiliations = schedule.affiliations_active_on_date(self.source_assignment.cleaning_day.date).\
            exclude(cleaner=self.source_assignment.cleaner)

        cleaning_day = self.source_assignment.cleaning_day
        active_affiliations = active_affiliations.exclude(cleaner__in=cleaning_day.excluded.all())

        candidates = []
        for affiliation in active_affiliations:
            if affiliation.cleaner.is_eligible_for_date(self.source_assignment.cleaning_day.date):
                candidates.append(affiliation.cleaner)

        logging.debug("------------ Looking for replacement cleaners -----------")

        for cleaner in candidates:
            logging.debug(
                "{}:  Duties today:{}".format(cleaner.name,
                                              cleaner.nr_assignments_on_day(self.source_assignment.cleaning_day.date)))

            assignments_in_future = schedule.assignment_set.filter(cleaner=cleaner, cleaning_day__date__gt=timezone.now().date())

            for assignment in assignments_in_future:
                if self.source_assignment.cleaner.is_eligible_for_date(assignment.cleaning_day.date):
                    self.destinations.add(assignment)
