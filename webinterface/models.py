from django.db import models
from django.db.utils import OperationalError
from operator import itemgetter
import datetime
from django.contrib.auth.hashers import make_password
from django.utils.text import slugify
import logging
from django.contrib.auth.models import User
from django.utils import timezone
import calendar
import time


# def correct_dates_to_due_day(days):
#     return correct_dates_to_weekday(days, 6)
#
#
# def correct_dates_to_weekday(days, weekday):
#     """
#     Days is a date or list of timezone.date objects you want converted. 0 = Monday, 6 = Sunday
#     The corrected weekday/s will always lie in the same week as days.
#     """
#     if isinstance(days, list):
#         corrected_days = []
#         for day in days:
#             if isinstance(day, datetime.date):
#                 # To prevent overflow of day over datetime.date.max
#                 day = datetime.date(9999, 12, 26) if day > datetime.date(9999, 12, 26) else day
#                 day += timezone.timedelta(days=weekday - day.weekday())
#             corrected_days.append(day)
#         return corrected_days
#     elif isinstance(days, datetime.date):
#         # To prevent overflow of day over datetime.date.max
#         days = datetime.date(9999, 12, 26) if days > datetime.date(9999, 12, 26) else days
#         return days + timezone.timedelta(days=weekday - days.weekday())
#     return None


def date_to_epoch_week(date: datetime.date) -> int:
    if not isinstance(date, datetime.date):
        raise TypeError("In date_to_epoch_week: Argument must be of type datetime.date or datetime.datetime!")
    # Beginning of epoch has epoch week number 0 but date number 3 (is a Thursday), so we subtract 4 days from input
    epoch_seconds = calendar.timegm(date.timetuple())
    return int((epoch_seconds / 60 / 60 / 24 - 4) / 7)


def epoch_week_to_monday(week: int) -> datetime.date:
    if not isinstance(week, int):
        raise TypeError("In epoch_week_to_monday: Argument must be an int!")
    epoch_seconds = (week * 7 + 4) * 24 * 60 * 60
    return datetime.date.fromtimestamp(time.mktime(time.gmtime(epoch_seconds)))


def current_epoch_week():
    return date_to_epoch_week(datetime.date.today())


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

    WEEKDAYS = ((0, 'Montag'), (1, 'Dienstag'), (2, 'Mittwoch'), (3, 'Donnerstag'),
                (4, 'Freitag'), (5, 'Samstag'), (6, 'Sonntag'))
    weekday = models.IntegerField(default=6, choices=WEEKDAYS)

    FREQUENCY_CHOICES = ((1, 'Jede Woche'), (2, 'Gerade Wochen'), (3, 'Ungerade Wochen'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

    disabled = models.BooleanField(default=False)

    objects = ScheduleQuerySet.as_manager()

    def __str__(self) -> str:
        return self.name

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.__last_cleaners_per_date = self.cleaners_per_date
        self.__last_frequency = self.frequency

    def deployment_ratios(self, week: int) -> list:
        """week must be a epoch week number as returned by date_to_epoch_week()"""
        ratios = []

        active_affiliations = Affiliation.objects.active_in_week_for_schedule(week, self)
        if active_affiliations.exists():
            for active_affiliation in active_affiliations:
                cleaner = active_affiliation.cleaner
                ratios.append([cleaner, cleaner.deployment_ratio_for_schedule(self)])
            return sorted(ratios, key=itemgetter(1), reverse=False)
        else:
            return []

    def occurs_in_week(self, week: int) -> bool:
        return self.frequency == 1 or \
               self.frequency == 2 and week % 2 == 0 or \
               self.frequency == 3 and week % 2 == 1

    """
    Creates assignments cover a timespan and has several more options.
    
    Week numbers must be epoch week numbers as returned by date_to_epoch_week().
    @param start_week: First week number on which a new Assignment will be created.
    @param end_week: Last week number on which a new Assignment will be created
    @param mode Sets the mode of creation:
    - 1(default): Delete existing Assignments and CleaningDays and regenerate them throughout time frame
    - 2: Keep existing Assignments and only create new ones where there are none already
    - 3: Only reassign Assignments on existing CleaningDays, don't generate new CleaningDays
    """
    def create_assignments_over_timespan(self, start_week: int, end_week: int, mode=1) -> None:
        """Generates new cleaning duties between week1 and week2."""
        if mode not in [1, 2, 3]:
            raise ValueError("In create_assignments_over_timespan: mode must be either 1,2 or 3!")

        min_week = min(start_week, end_week)
        max_week = max(start_week, end_week)
        cleaning_weeks = self.cleaningweek_set.enabled().filter(week__range=[min_week, max_week])

        if mode == 3 or mode == 1:
            self.assignment_set.filter(cleaning_week__in=cleaning_weeks).delete()
            if mode == 1:
                cleaning_weeks.delete()

        for week in range(min_week, max_week + 1):
            while self.create_assignment(week):
                # This loop enables Schedules with cleaners_per_date > 1 to be handled correctly, as each
                # call to create_assignment only assigns one Cleaner
                pass

    def create_assignment(self, week: int, bypass_check_if_occurs_in_week=False):
        if not self.occurs_in_week(week) and not bypass_check_if_occurs_in_week:
            logging.debug("NO ASSIGNMENT CREATED [Code01]: This schedule does not occur "
                          "in week {} as frequency is set to {}".
                          format(week, self.frequency))
            return False

        cleaning_week, was_created = self.cleaningweek_set.get_or_create(week=week)
        if cleaning_week.assignment_set.count() >= self.cleaners_per_date:
            logging.debug("NO ASSIGNMENT CREATED [Code02]: There are no open cleaning positions for week {}. "
                          "There are already {} Cleaners assigned for this week. ".
                          format(self.cleaners_per_date, week))
            return False

        ratios = self.deployment_ratios(week)
        if not ratios:
            logging.debug("NO ASSIGNMENT CREATED [Code03]: Deployment ratios are not defined for this date.")
            return False

        if logging.getLogger(__name__).getEffectiveLevel() >= logging.DEBUG:
            logging.debug('------------- CREATING NEW CLEANING DUTY FOR {} in week {} -------------'
                          .format(self.name, week))
            logging_text = "All cleaners' ratios: "
            for cleaner, ratio in ratios:
                logging_text += "{}: {}".format(cleaner.name, round(ratio, 3)) + "  "
            logging.debug(logging_text)

        for cleaner, ratio in ratios:
            if cleaner in cleaning_week.excluded.all():
                logging.debug("   {} is excluded for this week. [Code11]".format(cleaner.name))
                continue
            if cleaner.is_eligible_for_week(week):
                logging.debug("   {} inserted! [Code21]".format(cleaner.name))
                return self.assignment_set.create(cleaner=cleaner, cleaning_week=cleaning_week)
            else:
                logging.debug("   {} already has {} duties today. [Code12]".format(
                    cleaner.name, cleaner.nr_assignments_in_week(week)))
        else:
            logging.debug("   All Cleaners are excluded or are already cleaning as much as they like. "
                          "We must choose {} [Code22]"
                          .format(ratios[0][0]))
            return self.assignment_set.create(cleaner=ratios[0][0], cleaning_week=cleaning_week)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.slug = slugify(self.name)
        super(Schedule, self).save(force_insert, force_update, using, update_fields)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__disabled = self.disabled

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        if self.pk and self.__disabled != self.disabled:
            for affiliation in self.affiliation_set.all():
                if affiliation.end > timezone.now().date():
                    affiliation.end = timezone.now().date()
                    affiliation.save()


class CleanerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            affiliation__beginning__lte=current_epoch_week(), affiliation__end__gte=current_epoch_week())

    def inactive(self):
        return self.exclude(
            affiliation__beginning__lte=current_epoch_week(), affiliation__end__gte=current_epoch_week())

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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
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
                beginning__lte=current_epoch_week(), end__gte=current_epoch_week()
            )
            return current_affiliation
        except Affiliation.DoesNotExist:
            return None

    def all_assignments_during_affiliation_with_schedule(self, schedule):
        assignments_while_affiliated = Assignment.objects.none()
        for affiliation in self.affiliation_set.filter(group__schedules=schedule).all():
            assignments_while_affiliated |= Assignment.objects.filter(
                cleaning_week__week__gte=affiliation.beginning, cleaning_week__week__lt=affiliation.end,
                cleaning_week__schedule=schedule)
        return assignments_while_affiliated

    def own_assignments_during_affiliation_with_schedule(self, schedule):
        return self.all_assignments_during_affiliation_with_schedule(schedule).filter(cleaner=self)

    def deployment_ratio_for_schedule(self, schedule):
        all_assignments = self.all_assignments_during_affiliation_with_schedule(schedule)
        nr_own_assignments = all_assignments.filter(cleaner=self).count()
        if nr_own_assignments != 0:
            return nr_own_assignments / all_assignments.count()
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

    def nr_assignments_in_week(self, week):
        return self.assignment_set.filter(cleaning_week__week=week).count()

    def is_eligible_for_week(self, week):
        nr_assignments_on_day = self.nr_assignments_in_week(week)
        return nr_assignments_on_day == 0 or nr_assignments_on_day == 1 and self.preference == 2 \
            or self.preference == 3

    def has_slack_id(self):
        return self.slack_id is not ''

    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        self.user.delete()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)

        if not self.user:
            self.user = User.objects.create(username=self.slug, password=make_password(self.slug))
        elif self.user.username != self.slug:
            self.user.username = self.slug
            self.user.set_password(self.slug)
            self.user.save()

        super().save(force_insert, force_update, using, update_fields)


class AffiliationQuerySet(models.QuerySet):
    def active_in_week(self, week):
        return self.filter(beginning__lte=week, end__gte=week)

    def active_in_week_for_schedule(self, week, schedule):
        return self.active_in_week(week).filter(group__schedules=schedule)


class Affiliation(models.Model):
    """
    The Affiliation model tracks Cleaners' belonging to Schedules over time.

    The Affiliation model meant to be a chain of time periods for each Cleaner with no two Affiliations of a Cleaner
    overlapping in time. This constraint is enforced by the model.
    """
    class Meta:
        ordering = ('-end',)
        unique_together = ('beginning', 'cleaner')

    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    group = models.ForeignKey(ScheduleGroup, on_delete=models.CASCADE)

    beginning = models.IntegerField()
    end = models.IntegerField()

    objects = AffiliationQuerySet.as_manager()

    def __str__(self):
        return self.cleaner.name+" in "+self.group.name+" from week"+str(self.beginning)+" to week"+str(self.end)

    def __init__(self, *args, **kwargs):
        super(Affiliation, self).__init__(*args, **kwargs)

        self.__previous_beginning = self.beginning
        self.__previous_end = self.end

        if self.pk:
            self.__previous_cleaner = self.cleaner
            self.__previous_group = self.group
        else:
            self.__previous_cleaner = None
            self.__previous_group = None

    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        interval_start = min(self.beginning, self.end)
        interval_end = max(self.beginning, self.end)
        for schedule in self.group.schedules.all():
            schedule.new_cleaning_duties(interval_start, interval_end, 3)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.__previous_cleaner and self.__previous_group:
            if self.__previous_cleaner != self.cleaner or self.__previous_group != self.group:
                raise OperationalError("Cleaner or ScheduleGroup of an Affiliation cannot be changed!")

        # TODO write validator(pk, current_beginning, proposed_beginning, ...) that can be used by form as well
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

        super().save(force_insert, force_update, using, update_fields)

        try:
            overlapping_affiliation = self.cleaner.affiliation_set.exclude(pk=self.pk).get(
                end__gte=self.beginning, beginning__lte=self.beginning)

            # In overlap.save(), the Assignments in the overlapping dates are re-assigned.
            # For that reason we don't need to reassign those again
            overlapping_affiliation.end = self.beginning
            overlapping_affiliation.save()
        except Affiliation.DoesNotExist:
            pass

        for (prev, curr) in [(self.__previous_beginning, self.beginning), (self.__previous_end, self.end)]:
            if not prev or prev == curr:
                continue
            interval_start = min(prev, curr)
            interval_end = max(prev, curr)
            Assignment.objects. \
                filter(cleaning_week__week__gte=interval_start). \
                filter(cleaning_week__week__lte=interval_end). \
                delete()
            for schedule in self.group.schedules.all():
                schedule.new_cleaning_duties(interval_start, interval_end, 3)

        return


class CleaningWeekQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)

    def with_assignments(self):
        # We MUST use exclude here because filtering for __isnull=False will cause each CleaningDay to be as often
        # in the QuerySet as it has Assignments in its assignment_set
        return self.exclude(assignment__isnull=True)

    def no_assignments(self):
        return self.filter(assignment__isnull=True)


class CleaningWeek(models.Model):
    class Meta:
        ordering = ('-week',)
        unique_together = ('week', 'schedule')
    week = models.IntegerField()
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    disabled = models.BooleanField(default=False)

    objects = CleaningWeekQuerySet.as_manager()

    def __str__(self):
        return "{}: Week {}".format(self.schedule.name, self.week)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def has_tasks(self):
        return self.task_set.exists()

    def is_active(self):
        return self.task_set.active().exists()

    def is_passed(self):
        return self.has_tasks() and not self.task_set.in_future().exists() and not self.is_active()

    def is_in_future(self):
        return self.task_set.in_future().exists() and not self.is_active()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # TODO When created, populate task_set

        # if self.date != self.__previous_date:
        #     date_difference = self.__previous_date - self.date
        #     for task in self.task_set.all():
        #         task.start_date -= date_difference
        #         task.end_date -= date_difference
        #         task.save()
        super().save(force_insert, force_update, using, update_fields)


class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=timezone.now().date())

    cleaning_week = models.ForeignKey(CleaningWeek, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    class Meta:
        ordering = ('-cleaning_week__week',)

    def __str__(self):
        return "{}: {}, {} ".format(
            self.cleaning_week.schedule.name, self.cleaner.name, self.assignment_date().strftime('%d-%b-%Y'))

    def assignment_date(self):
        return epoch_week_to_monday(self.cleaning_week.week) + datetime.timedelta(days=self.schedule.weekday)

    def cleaners_in_week_for_schedule(self):
        return Cleaner.objects.filter(assignment__cleaning_week=self.cleaning_week)

    def cleaning_buddies(self):
        return self.cleaners_in_week_for_schedule().exclude(pk=self.cleaner.pk)

    def is_source_of_dutyswitch(self):
        duty_switch = DutySwitch.objects.filter(source_assignment=self)
        if duty_switch.exists():
            return duty_switch.first()
        else:
            return None


class TaskBase(models.Model):
    task_name = models.CharField(max_length=20)
    task_help_text = models.CharField(max_length=200)

    def __str__(self):
        return self.task_name


class TaskTemplateQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


class TaskTemplate(TaskBase):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    task_disabled = models.BooleanField(default=False)

    objects = TaskTemplateQuerySet.as_manager()

    start_days_before = models.IntegerField(default=1)
    end_days_after = models.IntegerField(default=2)

    def start_day_to_weekday(self):
        return Schedule.WEEKDAYS[(self.schedule.weekday-self.start_days_before) % 7][1]

    def end_day_to_weekday(self):
        return Schedule.WEEKDAYS[(self.schedule.weekday+self.start_days_before) % 7][1]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.start_days_before + self.end_days_after > 6:
            raise OperationalError("The sum of start_days_before and end_days_after cannot be greater 6!")
        super().save(force_insert, force_update, using, update_fields)

        # TODO when newly created or changed, update tasks of upcoming CleaningDays


class TaskQuerySet(models.QuerySet):
    def cleaned(self):
        return self.filter(cleaned_by__isnull=True)

    def uncleaned(self):
        return self.exclude(cleaned_by__isnull=True)

    def expired(self):
        return self.filter(end_date__lte=timezone.now().date())

    def expired_uncleaned(self):
        return self.expired().filter(cleaned_by__isnull=True)

    def expired_cleaned(self):
        return self.expired().exclude(cleaned_by__isnull=True)

    def active(self):
        return self.filter(start_date__lte=timezone.now().date(), end_date__gte=timezone.now().date())

    def active_uncleaned(self):
        return self.active().filter(cleaned_by__isnull=True)

    def active_cleaned(self):
        return self.active().exclude(cleaned_by__isnull=True)

    def in_future(self):
        return self.filter(start_date__gt=timezone.now().date())


class TaskManager(models.Manager):
    def create_from_template(self, template, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = template.name
        if 'help_text' not in kwargs:
            kwargs['help_text'] = template.help_text
        kwargs['start_date'] = kwargs['cleaning_day'] - timezone.timedelta(days=template.start_days_before)
        kwargs['end_date'] = kwargs['cleaning_day'] + timezone.timedelta(days=template.end_days_after)
        self.create(**kwargs)


class Task(TaskBase):
    cleaning_week = models.ForeignKey(CleaningWeek, on_delete=models.CASCADE)
    cleaned_by = models.ForeignKey(Assignment, null=True, on_delete=models.SET_NULL)

    start_date = models.DateField()
    end_date = models.DateField()

    objects = TaskManager.from_queryset(TaskQuerySet)()


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
                       self.source_assignment.assignment_date().strftime('%d-%b-%Y'),
                       self.selected_assignment.cleaner.name,
                       self.selected_assignment.assignment_date().strftime('%d-%b-%Y'),
                       self.status)
        else:
            return "Source: {} on {}  -  Selected:            -  Status: {} ". \
                format(self.source_assignment.cleaner.name,
                       self.source_assignment.assignment_date().strftime('%d-%b-%Y'),
                       self.status)

    def destinations_without_source_and_selected(self):
        destinations = self.destinations.exclude(pk=self.source_assignment.pk)
        if self.selected_assignment:
            destinations = destinations.exclude(pk=self.selected_assignment.pk)
        return destinations

    def set_selected(self, assignment):
        self.selected_assignment = assignment
        self.status = 1
        self.save()

    def selected_was_accepted(self):
        cleaning_week = self.source_assignment.cleaning_week

        cleaning_week.excluded.add(self.source_assignment.cleaner)

        source_cleaning_week = self.source_assignment.cleaning_week
        self.source_assignment.cleaning_week = self.selected_assignment.cleaning_week
        self.source_assignment.save()
        self.selected_assignment.cleaning_week = source_cleaning_week
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
        schedule = self.source_assignment.cleaning_week.schedule

        active_affiliations = Affiliation.objects.active_on_date_for_schedule(
            self.source_assignment.cleaning_week.week, schedule).exclude(
            cleaner=self.source_assignment.cleaner, cleaner__in=self.source_assignment.cleaning_week.excluded.all())

        candidates = []
        for affiliation in active_affiliations:
            if affiliation.cleaner.is_eligible_for_week(self.source_assignment.cleaning_week.week):
                candidates.append(affiliation.cleaner)

        logging.debug("------------ Looking for replacement cleaners -----------")

        for cleaner in candidates:
            logging.debug(
                "{}:  Duties on {}: {}".format(self.source_assignment.assignment_date(), cleaner.name,
                                               cleaner.nr_assignments_on_day(self.source_assignment.assignment_date())))

            assignments_in_future = schedule.assignment_set.filter(
                cleaner=cleaner, cleaning_week__week__gt=current_epoch_week())

            for assignment in assignments_in_future.all():
                if self.source_assignment.cleaner.is_eligible_for_week(assignment.cleaning_week.week):
                    self.destinations.add(assignment)
