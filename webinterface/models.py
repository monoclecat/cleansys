from django.db import models
from operator import itemgetter
import datetime
from django.db.models.signals import m2m_changed
from django.utils.text import slugify
from django.core.paginator import Paginator
import logging


def correct_dates_to_weekday(days, weekday):
    """Days is a date or list of datetime.date objects you want converted. 0 = Monday, 6 = Sunday"""
    if isinstance(days, list):
        corrected_days = []
        for day in days:
            if day:
                day += datetime.timedelta(days=weekday - day.weekday())
            corrected_days.append(day)
        return corrected_days
    elif isinstance(days, datetime.date):
        return days + datetime.timedelta(days=weekday - days.weekday())
    return None


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
        return self.tasks.split(",")

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

        active_cleaners_on_date = Cleaner.objects.filter(schedule_group__schedules=self,
                                                         moved_out__gte=for_date, moved_in__lte=for_date)
        #for group in self.schedule_group.all():
        #    active_cleaners_on_date += list(group.cleaners.filter(moved_out__gte=for_date, moved_in__lte=for_date))

        if active_cleaners_on_date:
            proportion__cleaners_assigned_per_week = self.cleaners_per_date / len(active_cleaners_on_date)

            iterate_over = cleaners if cleaners else active_cleaners_on_date

            for cleaner in iterate_over:
                all_assignments = self.assignment_set.filter(date__range=(cleaner.moved_in, cleaner.moved_out))

                if all_assignments.exists():
                    proportion__self_assigned = all_assignments.filter(
                        cleaner=cleaner).count() / all_assignments.count()
                    ratios.append([cleaner,
                                   proportion__self_assigned / proportion__cleaners_assigned_per_week])
                else:
                    ratios.append([cleaner, 0])

        return sorted(ratios, key=itemgetter(1), reverse=False)

    def defined_on_date(self, date):
        return self.frequency == 1 or self.frequency == 2 and date.isocalendar()[1] % 2 == 0 or \
               self.frequency == 3 and date.isocalendar()[1] % 2 == 1

    def new_cleaning_duties(self, date1, date2, clear_existing=True):
        """Generates new cleaning duties between date1 and date2. To ensure better distribution of cleaners,
        all duties in time frame are deleted."""
        start_date = min(date1, date2)
        end_date = max(date1, date2)
        one_week = datetime.timedelta(days=7)

        if clear_existing:
            self.assignment_set.filter(date__range=(start_date, end_date)).delete()

        date_iterator = start_date
        while date_iterator <= end_date:
            if clear_existing or not clear_existing and not self.assignment_set.filter(date=date_iterator).exists():
                self.assign_cleaning_duty(date_iterator)
            date_iterator += one_week

    def assign_cleaning_duty(self, date):
        """Generates a new Duty and assigns Cleaners to it.
        If self.frequency is set to 'Even weeks' and it is not an even week, this function fails silently.
        The same is true if self.frequency is set to 'Odd weeks'."""

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
                for i in range(min(self.cleaners_per_date, len(ratios))):
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

            logging.debug("")


class ScheduleGroup(models.Model):
    class Meta:
        ordering = ("name", )
    name = models.CharField(max_length=30, unique=True)
    schedules = models.ManyToManyField(Schedule)

    def __str__(self):
        return self.name


class Cleaner(models.Model):
    class Meta:
        ordering = ('name',)
    name = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=10, unique=True)
    moved_in = models.DateField()
    moved_out = models.DateField()
    slack_id = models.CharField(max_length=10, null=True)
    schedule_group = models.ForeignKey(ScheduleGroup, on_delete=models.SET_NULL, null=True)

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

    def nr_assignments_on_day(self, date):
        return self.assignment_set.filter(date=date).count()

    def delete(self, using=None, keep_parents=False):
        for schedule in self.schedule_group.schedules.all():
            schedule.new_cleaning_duties(self.moved_in, self.moved_out)
        super().delete(using, keep_parents)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using, update_fields)

        if self.moved_out != self.__last_moved_out:
            prev_last_duty, new_last_duty = correct_dates_to_weekday([self.__last_moved_out, self.moved_out], 6)
            if prev_last_duty != new_last_duty:
                for schedule in self.schedule_group.schedules.all():
                    schedule.new_cleaning_duties(prev_last_duty, new_last_duty, True)

        if self.moved_in != self.__last_moved_in:
            prev_first_duty, new_first_duty = correct_dates_to_weekday([self.__last_moved_in, self.moved_in], 6)
            if prev_first_duty != new_first_duty:
                for schedule in self.schedule_group.schedules.all():
                    schedule.new_cleaning_duties(prev_first_duty, new_first_duty, True)

        if self.schedule_group != self.__last_group:
            if self.__last_group:
                schedules_to_reassign = self.schedule_group.schedules.intersection(self.__last_group.schedules)
            else:
                schedules_to_reassign = self.schedule_group.schedules
            print(schedules_to_reassign)
            for schedule in schedules_to_reassign.all():
                schedule.new_cleaning_duties(self.moved_in, self.moved_out)


class Task(models.Model):
    name = models.CharField(max_length=20)
    help_text = models.CharField(max_length=200, null=True)
    cleaned_by = models.ForeignKey(Cleaner, null=True, on_delete=models.SET_NULL)


class Complaint(models.Model):
    tasks_in_question = models.ManyToManyField(Task)
    comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=datetime.date.today)


# def group_cleaners_changed(instance, action, pk_set, **kwargs):
#     if action == 'post_add' or action == 'post_remove':
#         dates_to_delete = []
#         one_week = datetime.timedelta(days=7)
#         for cleaner_pk in pk_set:
#             cleaner = Cleaner.objects.get(pk=cleaner_pk)
#             first_duty, last_duty = correct_dates_to_weekday([min(cleaner.moved_in, datetime.date.today()),
#                                                               cleaner.moved_out], 6)
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


class CleaningDay(models.Model):
    tasks = models.ManyToManyField(Task)
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def initiate_tasks(self):
        schedule = self.schedule
        task_list = schedule.get_tasks()
        for task in task_list:
            self.tasks.create(name=task)

    def delete(self, using=None, keep_parents=False):
        self.tasks.all().delete()
        super().delete(using, keep_parents)


class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=datetime.date.today)
    date = models.DateField()
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return self.schedule.name + ": " + self.cleaner.name + " on the " + str(self.date)

    def cleaners_on_date_for_schedule(self):
        return Cleaner.objects.filter(assignment__schedule=self.schedule,
                                      assignment__date=self.date)

    def cleaning_buddies(self):
        return self.cleaners_on_date_for_schedule().exclude(pk=self.cleaner.pk)

    def cleaning_day(self):
        try:
            return self.schedule.cleaningday_set.get(date=self.date)
        except CleaningDay.DoesNotExist:
            return None


class DutySwitch(models.Model):
    class Meta:
        ordering = ('created',)
    created = models.DateField(auto_now_add=datetime.date.today)

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
                schedulegroup__schedule=schedule).exclude(
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
                    cleaner=cleaner, date__gt=datetime.date.today())

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

            if not self.destinations:
                if source_is_already_assigned:
                    for assignment in source_is_already_assigned:
                        self.destinations.add(assignment)
                else:
                    for assignment in one_duty_cleaners:
                        self.destinations.add(assignment)

