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
    if isinstance(days, datetime.date):
        return days + datetime.timedelta(days=weekday - days.weekday())


class Cleaner(models.Model):
    name = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=10, unique=True)
    moved_in = models.DateField()
    moved_out = models.DateField()
    slack_id = models.CharField(max_length=10, null=True)

    def __init__(self, *args, **kwargs):
        super(Cleaner, self).__init__(*args, **kwargs)
        self.__last_moved_in = self.moved_in
        self.__last_moved_out = self.moved_out

    def __str__(self):
        return self.name

    def rejected_dutyswitch_requests(self):
        return DutySwitch.objects.filter(source_cleaner=self, status=2)

    def dutyswitch_requests_received(self):
        return DutySwitch.objects.filter(selected_cleaner=self)

    def pending_dutyswitch_requests(self):
        return DutySwitch.objects.filter(source_cleaner=self, status=1)

    def delete(self, using=None, keep_parents=False):
        try:
            associated_group = CleaningScheduleGroup.objects.get(cleaners=self)
            associated_schedules = associated_group.cleaningschedule_set.all()
            for schedule in associated_schedules:
                schedule.cleaners.remove(self)
        except CleaningScheduleGroup.DoesNotExist:
            pass
        super().delete(using, keep_parents)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using, update_fields)

        associated_group = CleaningScheduleGroup.objects.filter(cleaners=self)
        if associated_group.exists():
            associated_group = associated_group.first()

            if self.moved_out != self.__last_moved_out:
                prev_last_duty, new_last_duty = correct_dates_to_weekday([self.__last_moved_out, self.moved_out], 6)
                if prev_last_duty != new_last_duty:
                    for schedule in CleaningSchedule.objects.filter(schedule_group=associated_group):
                        schedule.new_cleaning_duties(prev_last_duty, new_last_duty, True)

            if self.moved_in != self.__last_moved_in:
                prev_first_duty, new_first_duty = correct_dates_to_weekday([self.__last_moved_in, self.moved_in], 6)
                if prev_first_duty != new_first_duty:
                    for schedule in CleaningSchedule.objects.filter(schedule_group=associated_group):
                        schedule.new_cleaning_duties(prev_first_duty, new_first_duty, True)


class Task(models.Model):
    name = models.CharField(max_length=20)
    help_text = models.CharField(max_length=200, null=True)


class InfoForDate(models.Model):
    tasks = models.ManyToManyField(Task)
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner)


class Complaint(models.Model):
    tasks_in_question = models.ManyToManyField(Task)
    comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=datetime.date.today)


class Assignment(models.Model):
    class Meta:
        ordering = ('created',)

    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=datetime.date.today)
    date = models.DateField()
    cleaned = models.ManyToManyField(Task)

    def __str__(self):
        return self.cleaner.name

    def open_tasks(self):
        # TODO
        pass

    def task_completed(self):
        # TODO
        pass


class CleaningScheduleGroup(models.Model):
    class Meta:
        ordering = ("name", )
    name = models.CharField(max_length=30, unique=True)
    cleaners = models.ManyToManyField(Cleaner)

    def __str__(self):
        return self.name


class CleaningSchedule(models.Model):
    name = models.CharField(max_length=20, unique=True)
    slug = models.CharField(max_length=20, unique=True)

    CLEANERS_PER_DATE_CHOICES = ((1, 'Einen'), (2, 'Zwei'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Jede Woche'), (2, 'Gerade Wochen'), (3, 'Ungerade Wochen'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

    assignments = models.ManyToManyField(Assignment)
    info_for_dates = models.ManyToManyField(InfoForDate)

    schedule_group = models.ManyToManyField(CleaningScheduleGroup, blank=True)

    tasks = models.CharField(max_length=200, null=True)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(CleaningSchedule, self).__init__(*args, **kwargs)
        self.__last_cleaners_per_date = self.cleaners_per_date
        self.__last_frequency = self.frequency

    def get_tasks(self):
        return self.tasks.split(",")

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.slug = slugify(self.name)
        super(CleaningSchedule, self).save(force_insert, force_update, using, update_fields)

        if self.cleaners_per_date != self.__last_cleaners_per_date or self.frequency != self.__last_frequency:
            all_duty_dates = list(self.info_for_dates.values_list('date', flat=True))
            self.info_for_dates.all().delete()
            self.assignments.all().delete()
            for date in all_duty_dates:
                self.assign_cleaning_duty(date)

    def delete(self, using=None, keep_parents=False):
        self.info_for_dates.all().delete()
        self.assignments.all().delete()
        super().delete(using, keep_parents)

    def deployment_ratios(self, for_date, cleaners=None):
        """Returns <number of duties a cleaner cleans in>/<total number of duties> on date for_date.
        Ratios are calculated over a time window that stretches into the past and the future, ignoring
        duties that have no cleaners assigned. If you wish to know only the ratio of a select number
        of cleaners, pass them in a list in the cleaners argument. Otherwise all ratios will be returned."""
        ratios = []

        active_cleaners_on_date = []
        for group in self.schedule_group.all():
            active_cleaners_on_date += list(group.cleaners.filter(moved_out__gte=for_date, moved_in__lte=for_date))

        if active_cleaners_on_date:
            proportion__cleaners_assigned_per_week = self.cleaners_per_date / len(active_cleaners_on_date)

            iterate_over = cleaners if cleaners else active_cleaners_on_date

            for cleaner in iterate_over:
                all_assignments = self.assignments.filter(date__range=(cleaner.moved_in, cleaner.moved_out))

                if all_assignments.exists():
                    proportion__self_assigned = all_assignments.filter(
                        cleaner=cleaner).count() / all_assignments.count()
                    ratios.append([cleaner,
                                   proportion__self_assigned / proportion__cleaners_assigned_per_week])
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
            self.assignments.filter(date__range=(start_date, end_date)).delete()

        date_iterator = start_date
        while date_iterator <= end_date:
            if clear_existing or not clear_existing and not self.assignments.filter(date=date_iterator).exists():
                self.assign_cleaning_duty(date_iterator)
            date_iterator += one_week

    def assign_cleaning_duty(self, date):
        """Generates a new Duty and assigns Cleaners to it.
        If self.frequency is set to 'Even weeks' and it is not an even week, this function fails silently.
        The same is true if self.frequency is set to 'Odd weeks'."""

        if self.defined_on_date(date):
            info_for_date, was_created = self.info_for_dates.get_or_create(date=date)

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
                        if not self.assignments.filter(date=date, cleaner=cleaner).exists() and \
                                cleaner not in info_for_date.excluded.all():
                            if cleaner.assignment_set.filter(date=date).count() == 0:
                                self.assignments.create(date=date, cleaner=cleaner)
                                logging.debug("          {} inserted!".format(cleaner.name))
                                break
                            elif not last_resort_cleaner and cleaner.assignment_set.filter(date=date).count() == 1:
                                last_resort_cleaner = cleaner
                            logging.debug("{} is not free.".format(cleaner.name))
                    else:
                        if last_resort_cleaner:
                            logging.debug("Nobody has 0 duties on date so we choose {}".format(last_resort_cleaner))
                            self.assignments.create(date=date, cleaner=last_resort_cleaner)
                        else:
                            logging.debug("NOBODY HAS 1 DUTY ON DATE! We choose {}".format(ratios[0][0]))
                            self.assignments.create(date=date, cleaner=ratios[0][0])

            logging.debug("")


def group_cleaners_changed(instance, action, pk_set, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        dates_to_delete = []
        one_week = datetime.timedelta(days=7)
        for cleaner_pk in pk_set:
            cleaner = Cleaner.objects.get(pk=cleaner_pk)
            first_duty, last_duty = correct_dates_to_weekday([min(cleaner.moved_in, datetime.date.today()),
                                                              cleaner.moved_out], 6)
            date_iterator = first_duty
            while date_iterator <= last_duty:
                if date_iterator not in dates_to_delete:
                    dates_to_delete.append(date_iterator)
                date_iterator += one_week

        for schedule in CleaningSchedule.objects.filter(schedule_group=instance):
            dates_to_redistribute = []
            for date in dates_to_delete:
                duty = schedule.duties.filter(date=date)
                if duty.exists():
                    duty.delete()
                    dates_to_redistribute.append(date)
            for date in dates_to_redistribute:
                schedule.assign_cleaning_duty(date)


m2m_changed.connect(group_cleaners_changed, sender=CleaningScheduleGroup.cleaners.through)


class DutySwitch(models.Model):
    created = models.DateField(auto_now_add=datetime.date.today)

    source_assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)

    selected_assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True)

    destinations = models.ManyToManyField(Assignment)

    STATES = ((0, 'Waiting on source choice'), (1, 'Waiting on approval for selected'), (2, 'Selected was rejected'))
    status = models.IntegerField(choices=STATES, default=0)
    # DutySwitch object gets created in statue 0 as Cleaner needs to select a desired Duty destination.
    # When the desired Duty is selected the status is set to 1 because we need approval
    # from the destination to commence switching.
    # If the destination denies approval, status is set to 2 because the source needs to select a new
    # destination. The cycle begins from the start

    def set_selected(self, assignment):
        self.selected_assignment = assignment
        self.status = 1

    def selected_was_accepted(self):
        try:
            info_for_date = InfoForDate.objects.get(date=self.source_assignment.date)
        except InfoForDate.DoesNotExist:
            return
        info_for_date.excluded.add(self.source_assignment.cleaner)

        Assignment.objects.create(date=self.source_assignment.date, cleaner=self.selected_assignment.cleaner)
        Assignment.objects.create(date=self.selected_assignment.date, cleaner=self.source_assignment.cleaner)
        # TODO Remember to only take first n assignments when selecting assignments on date, we are not deleting old assignments!

        self.delete()

    def selected_was_cancelled(self):
        self.selected_assignment = None
        self.status = 0

    def selected_was_rejected(self):
        self.destinations.remove(self.selected_assignment)
        self.selected_assignment = None
        self.status = 2

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.destinations:
            schedule = self.source_assignment.cleaningschedule_set.first()

            ratios = schedule.deployment_ratios(self.source_assignment.date)
            logging.debug("------------ Looking for replacement cleaners -----------")
            free_cleaners = models.ManyToManyField(Assignment)
            one_duty_cleaners = models.ManyToManyField(Assignment)
            for cleaner, ratio in ratios:
                logging.debug(
                    "{}:   Not in duty:{} Duties today:{}".
                        format(cleaner.name,
                               schedule.assignments.filter(date=self.source_assignment.date, cleaner=cleaner).exists(),
                               cleaner.duty_set.filter(date=self.source_assignment.date).count()))

                if not schedule.assignments.filter(date=self.source_assignment.date, cleaner=cleaner).exists():
                    if cleaner.assignment_set.filter(date=self.source_assignment.date).count() == 0:
                        free_cleaners.add(schedule.assignments.filter(cleaners=cleaner, date__gt=self.source_assignment.date))
                    elif cleaner.assignment_set.filter(date=self.source_assignment.date).count() == 1:
                        one_duty_cleaners.add(schedule.assignments.filter(cleaners=cleaner, date__gt=self.source_assignment.date))

            if free_cleaners:
                self.destinations = free_cleaners
            else:
                self.destinations = one_duty_cleaners

        super().save(force_insert, force_update, using, update_fields)

