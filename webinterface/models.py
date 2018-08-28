from django.db import models
from django.db.utils import OperationalError
from operator import itemgetter
import datetime
from django.contrib.auth.hashers import make_password
from django.utils.text import slugify
import logging
from django.contrib.auth.models import User
from django.utils import timezone


def correct_dates_to_due_day(days):
    return correct_dates_to_weekday(days, 6)


def correct_dates_to_weekday(days, weekday):
    """
    Days is a date or list of timezone.date objects you want converted. 0 = Monday, 6 = Sunday
    The corrected weekday/s will always lie in the same week as days.
    """
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


class ScheduleQuerySet(models.QuerySet):
    def enabled(self):
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

    disabled = models.BooleanField(default=False)

    objects = ScheduleQuerySet.as_manager()

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.__last_cleaners_per_date = self.cleaners_per_date
        self.__last_frequency = self.frequency

    def get_active_assignments(self):
        """Returns Assignments for this Schedule that are active today or were have
        recently passed (if no Assignment is currently active) """
        # TODO

    def get_current_cleaning_day(self):
        """Returns Assignments for this Schedule that are active today or were have
        recently passed (if no Assignment is currently active) """
        # TODO

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.slug = slugify(self.name)
        super(Schedule, self).save(force_insert, force_update, using, update_fields)

        if self.cleaners_per_date != self.__last_cleaners_per_date or self.frequency != self.__last_frequency:
            raise OperationalError("cleaners_per_date and frequency cannot be changed!")

    def deployment_ratios(self, date):
        ratios = []

        active_affiliations = Affiliation.objects.active_on_date_for_schedule(date, self)
        if active_affiliations.exists():
            for active_affiliation in active_affiliations:
                cleaner = active_affiliation.cleaner
                ratios.append([cleaner, cleaner.deployment_ratio_for_schedule(self)])
            return sorted(ratios, key=itemgetter(1), reverse=False)
        else:
            return []

    def defined_on_date(self, date):
        return self.frequency == 1 or self.frequency == 2 and date.isocalendar()[1] % 2 == 0 or \
               self.frequency == 3 and date.isocalendar()[1] % 2 == 1

    """
    Like create_assignment, only that it can cover a timespan and has several more options.
    
    date1 does not have to be smaller than date2 or vice-versa. 
    @param date1 First date of timeframe, will be corrected to the due-day
    @param date2 Second date of timeframe, will be corrected to the due-day
    @param mode Sets the mode of creation:
    - 1: Delete existing Assignments in timeframe and create new Assignments throughout timeframe
    - 2: Keep existing Assignments and only create new ones where there are none already
    - 3: Only reassign Assignments on existing CleaningDays, don't generate new CleaningDays
    """
    def new_cleaning_duties(self, date1, date2, mode=1):
        """Generates new cleaning duties between date1 and date2."""
        start_date, end_date = correct_dates_to_due_day([min(date1, date2), max(date1, date2)])
        one_week = timezone.timedelta(days=7)

        date_iterator = start_date
        while date_iterator < end_date:
            if mode == 1:
                self.assignment_set.filter(cleaning_day__date=date_iterator).delete()
            elif mode == 2:
                pass
            elif mode == 3:
                assignments_on_date = self.assignment_set.filter(date=date_iterator)
                if assignments_on_date.exists():
                    assignments_on_date.delete()
                else:
                    date_iterator += one_week
                    continue
            else:
                raise OperationalError("Invalid mode!")
            while self.create_assignment(date_iterator):
                # This loop enables Schedules with cleaners_per_date > 1 to be handled correctly, as each
                # call to create_assignment only assigns one Cleaner
                pass
            date_iterator += one_week

    def create_assignment(self, date):
        """Generates a new Duty and assigns Cleaners to it.
        If the Schedule is not defined on date (see defined_on_date()), then this function fails silently."""

        corrected_date = correct_dates_to_due_day(date)
        if self.defined_on_date(corrected_date):
            cleaning_day, was_created = self.cleaningday_set.get_or_create(date=corrected_date)

            ratios = self.deployment_ratios(corrected_date)

            if logging.getLogger(__name__).getEffectiveLevel() >= logging.DEBUG:
                logging.debug('------------- CREATING NEW CLEANING DUTY FOR {} on the {} -------------'
                              .format(self.name, corrected_date))
                logging_text = "All cleaners' ratios: "
                for cleaner, ratio in ratios:
                    logging_text += "{}: {}".format(cleaner.name, round(ratio, 3)) + "  "
                logging.debug(logging_text)

            if ratios and cleaning_day.assignment_set.count() < self.cleaners_per_date:
                for cleaner, ratio in ratios:
                    if cleaner.is_eligible_for_date(corrected_date) and cleaner not in cleaning_day.excluded.all():
                        logging.debug("   {} inserted!".format(cleaner.name))
                        return self.assignment_set.create(cleaner=cleaner, cleaning_day=cleaning_day)
                    else:
                        logging.debug("   {} already has {} duties today.".format(
                            cleaner.name, cleaner.nr_assignments_on_day(corrected_date)))
                else:
                    logging.debug("   Cleaner's preferences result in no cleaner, we must choose {}"
                                  .format(ratios[0][0]))
                    return self.assignment_set.create(cleaner=ratios[0][0], cleaning_day=cleaning_day)
            else:
                return False
        else:
            return False


class ScheduleGroupQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


class ScheduleGroup(models.Model):
    """
    A ScheduleGroup can be thought of as the floor you're living on. It simplifies grouping of Cleaners.

    Cleaners can be affiliated to different ScheduleGroups over time, which is tracked by the Affiliation model.
    A ScheduleGroup should not be deleted (rather disabled), as this causes Affiliations to be deleted,
    creating holes in the affiliation history which can lead to issues in consistency and the assigning of
    duties to Cleaners.
    """
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


class Cleaner(models.Model):
    """
    The Cleaner is the representation of the physical person living in the house.

    The Cleaner is linked to a User and can state his/her preferences in cleaning.
    """
    class Meta:
        ordering = ('name',)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=20, unique=True)
    slug = models.CharField(max_length=20, unique=True)

    time_zone = models.CharField(max_length=30, default="Europe/Berlin")
    slack_id = models.CharField(max_length=10, default='')

    PREFERENCE = ((1, 'Ich möchte immer nur einen Putzdienst auf einmal machen müssen.'),
                  (2, 'Ich möchte höchstens zwei Putzdienste auf einmal machen müssen.'),
                  (3, 'Mir ist es egal, wie viele Putzdienste ich auf einmal habe.'))
    preference = models.IntegerField(choices=PREFERENCE, default=2)

    objects = CleanerQuerySet.as_manager()

    def __str__(self):
        return self.name

    def current_affiliation(self):
        try:
            current_affiliation = self.affiliation_set.get(
                beginning__lte=timezone.now().date(), end__gt=timezone.now().date())
            return current_affiliation
        except:
            return None

    def all_assignments_during_affiliation_with_schedule(self, schedule):
        affiliations_with_schedule = Affiliation.objects.filter(group__schedules=schedule)
        assignments_while_affiliated = Assignment.objects.none()
        if affiliations_with_schedule.exists():
            for affiliation in affiliations_with_schedule.all():
                assignments_while_affiliated |= Assignment.objects.filter(
                    cleaning_day__date__gte=affiliation.beginning, cleaning_day__date__lt=affiliation.end,
                    cleaning_day__schedule=schedule)
        return assignments_while_affiliated

    def own_assignments_during_affiliation_with_schedule(self, schedule):
        return self.all_assignments_during_affiliation_with_schedule(schedule).filter(cleaner=self)

    def deployment_ratio_for_schedule(self, schedule):
        all_assignments = self.all_assignments_during_affiliation_with_schedule(schedule)
        nr_own_assignments = all_assignments.filter(cleaner=self).count()
        if nr_own_assignments != 0:
            return all_assignments.count() / nr_own_assignments
        else:
            return 0

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
            new_password = make_password(None)
            self.user = User.objects.create(username=self.slug, password=new_password)
        elif self.user.username != self.slug:
            self.user.username = self.slug
            self.user.set_password(self.slug)
            self.user.save()

        super().save(force_insert, force_update, using, update_fields)


class AffiliationQuerySet(models.QuerySet):
    def active_on_date(self, date):
        return self.filter(beginning__lte=date, end__gt=date)

    def active_on_date_for_schedule(self, date, schedule):
        return self.active_on_date(date).filter(group__schedules=schedule)


class Affiliation(models.Model):
    """
    The Affiliation model tracks Cleaners' belonging to Schedules over time.

    The Affiliation model meant to be a chain of time periods for each Cleaner with no two Affiliations of a Cleaner
    overlapping in time. This constraint is enforced by the model.
    """
    class Meta:
        ordering = ('-end',)
        unique_together = ('beginning', 'cleaner')
    # TODO Make sure affiliations for a cleaner do NOT overlap in time!
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    group = models.ForeignKey(ScheduleGroup, on_delete=models.CASCADE)

    beginning = models.DateField()
    end = models.DateField(default=datetime.date.max)

    objects = AffiliationQuerySet.as_manager()

    def __str__(self):
        return self.cleaner.name+" in "+self.group.name+" from "+str(self.beginning)+" to "+str(self.end)

    def __init__(self, *args, **kwargs):
        super(Affiliation, self).__init__(*args, **kwargs)
        # TODO are these empty for newly created objects?
        self.__previous_beginning = self.beginning
        self.__previous_end = self.end
        self.__previous_cleaner = self.cleaner
        self.__previous_group = self.group

    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        interval_start = min(self.beginning, self.end)
        interval_end = max(self.beginning, self.end)
        for schedule in self.group.schedules.all():
            schedule.new_cleaning_duties(interval_start, interval_end, 3)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.__previous_cleaner != self.cleaner or self.__previous_group != self.group:
            raise OperationalError("Cleaner or ScheduleGroup of an Affiliation cannot be changed!")

        if self.beginning > self.end:
            raise OperationalError("The end of an Affiliation cannot lie before its beginning!")

        if self.pk:
            # Modifying an already created object
            beginning_was_set_before_beginning_of_these = \
                self.cleaner.affiliation_set.filter(
                    beginning__lt=self.__previous_beginning, beginning__gte=self.beginning)
            if beginning_was_set_before_beginning_of_these.exists():
                raise OperationalError("You can't set the beginning before the beginning of another Affiliation of "
                                       "a Cleaner.")
        else:
            # Creating a new object
            if self.cleaner.affiliation_set.filter(beginning__gte=self.beginning).exclude(pk=self.pk).exists():
                # The proposed Affiliation shall begin before an existing Affiliation begins -> Not allowed!
                # Affiliations can only be chained behind each other in time
                raise OperationalError("Affiliation with beginning before beginning of another Affiliation of "
                                       "a Cleaner cannot be created!")

        try:
            overlap = self.cleaner.affiliation_set.exclude(pk=self.pk).get(
                end__gt=self.beginning, beginning__lt=self.beginning)

            # In overlap.save(), the Assignments in the overlapping dates are re-assigned.
            # For that reason we don't need to reassign those again
            interval_already_reassigned = [self.beginning, overlap.end]
            overlap.end = self.beginning
            overlap.save()
        except Affiliation.DoesNotExist:
            interval_already_reassigned = list()

        super().save(force_insert, force_update, using, update_fields)

        # TODO only do this for Assignments in future!
        reassigning_required = False
        interval_start = datetime.date.min
        interval_end = datetime.date.max
        if self.__previous_beginning != self.beginning:
            if interval_already_reassigned:
                # If an overlap has been fixed (see above), we can assume that the beginning has been moved ahead
                # Thus, the upper limit of the overlap is the lower bound of the interval left to reassign
                # The upper bound of the interval left to reassign must be the old beginning
                interval_start = interval_already_reassigned[1]
                interval_end = self.__previous_beginning
            else:
                interval_start = min(self.__previous_beginning, self.beginning)
                interval_end = max(self.__previous_beginning, self.beginning)
            reassigning_required = True
        if self.__previous_end != self.end:
            if reassigning_required:
                interval_end = max(self.__previous_end, self.end, interval_end)
            else:
                interval_start = min(self.__previous_end, self.end)
                interval_end = max(self.__previous_end, self.end)
                reassigning_required = True
        if reassigning_required and interval_start != interval_end:
            for schedule in self.group.schedules.all():
                schedule.new_cleaning_duties(interval_start, interval_end, 3)


class CleaningDay(models.Model):
    class Meta:
        ordering = ('-date',)
        unique_together = ('date', 'schedule')
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return "{}: {}".format(self.schedule.name, self.date.strftime('%d-%b-%Y'))

    def cleaning_start_date(self):
        can_start__days__prior = 6 - min(self.schedule.task_set.enabled().values_list('start_weekday', flat=True))
        return self.date - datetime.timedelta(days=can_start__days__prior)

    def cleaning_end_date(self):
        can_end__days__after = 1 + max(self.schedule.task_set.enabled().values_list('end_weekday', flat=True))
        return self.date - datetime.timedelta(days=can_end__days__after)

    def task_list(self):
        """
        Returns a list of: [Task object, cleaned by Assignment, cleanable]
        cleanable: today lies in the time window in which the Task can be cleaned
        """
        task_list = list()
        for task in self.schedule.task_set.enabled():
            temp_list = [task]

            task_cleaned_by = self.assignment_set.filter(tasks_cleaned=task)
            if task_cleaned_by.exists():
                temp_list.append(task_cleaned_by.first())
            else:
                temp_list.append(None)

            can_start__days__prior = 6 - task.start_weekday
            can_start__days__after = 1 + task.end_weekday
            start_date = self.date - timezone.timedelta(days=can_start__days__prior)
            end_date = self.date + timezone.timedelta(days=can_start__days__after)
            temp_list.append(start_date <= timezone.now().date() <= end_date)

            task_list.append(temp_list)
        return task_list


class TaskQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


class Task(models.Model):
    WEEKDAYS = ((0, 'Montag'), (1, 'Dienstag'), (2, 'Mittwoch'), (3, 'Donnerstag'), (4, 'Freitag'),
                (5, 'Samstag'), (6, 'Sonntag'))
    name = models.CharField(max_length=20)

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    start_weekday = models.IntegerField(choices=WEEKDAYS, default=5)
    end_weekday = models.IntegerField(choices=WEEKDAYS, default=1)

    disabled = models.BooleanField(default=False)

    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return self.name


class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=timezone.now().date())

    cleaning_day = models.ForeignKey(CleaningDay, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    tasks_cleaned = models.ManyToManyField(Task)

    class Meta:
        ordering = ('cleaning_day__date',)

    def __str__(self):
        return "{}: {}, {} ".format(self.cleaning_day.schedule.name, self.cleaner.name,
                                    self.cleaning_day.date.strftime('%d-%b-%Y'))

    def cleaners_on_date_for_schedule(self):
        return Cleaner.objects.filter(assignment__cleaning_day=self.cleaning_day)

    def cleaning_buddies(self):
        return self.cleaners_on_date_for_schedule().exclude(pk=self.cleaner.pk)

    def is_source_of_dutyswitch(self):
        duty_switch = DutySwitch.objects.filter(source_assignment=self)
        if duty_switch.exists():
            return duty_switch.first()
        else:
            return None


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
                format(self.source_assignment.cleaner.name,
                       self.source_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
                       self.selected_assignment.cleaner.name,
                       self.selected_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
                       self.status)
        else:
            return "Source: {} on {}  -  Selected:            -  Status: {} ". \
                format(self.source_assignment.cleaner.name,
                       self.source_assignment.cleaning_day.date.strftime('%d-%b-%Y'),
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
        schedule = self.source_assignment.cleaning_day.schedule

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

            assignments_in_future = schedule.assignment_set.filter(cleaner=cleaner,
                                                                   cleaning_day__date__gt=timezone.now().date())

            for assignment in assignments_in_future:
                if self.source_assignment.cleaner.is_eligible_for_date(assignment.cleaning_day.date):
                    self.destinations.add(assignment)
