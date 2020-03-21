from django.db import models
from django.db.utils import OperationalError
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
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
    epoch_seconds = calendar.timegm(date.timetuple())
    return int(((epoch_seconds / 60 / 60 / 24) + 3) / 7)


def epoch_week_to_monday(week: int) -> datetime.date:
    epoch_seconds = ((week * 7) - 3) * 24 * 60 * 60
    return datetime.date.fromtimestamp(time.mktime(time.gmtime(epoch_seconds)))


def epoch_week_to_sunday(week: int) -> datetime.date:
    epoch_seconds = ((week * 7) + 3) * 24 * 60 * 60
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
            while self.create_assignment(week=week):
                # This loop enables Schedules with cleaners_per_date > 1 to be handled correctly, as each
                # call to create_assignment only assigns one Cleaner
                pass

    def create_assignment(self, week: int, bypass_check_if_occurs_in_week=False, initiate_tasks=True):
        if not self.occurs_in_week(week) and not bypass_check_if_occurs_in_week:
            logging.debug("NO ASSIGNMENT CREATED [Code01]: This schedule does not occur "
                          "in week {} as frequency is set to {}".
                          format(week, self.frequency))
            return False

        cleaning_week, was_created = self.cleaningweek_set.get_or_create(week=week)
        if initiate_tasks:
            cleaning_week.create_missing_tasks()

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
    def active(self) -> QuerySet:
        return self.filter(
            affiliation__beginning__lte=current_epoch_week(), affiliation__end__gte=current_epoch_week())

    def inactive(self) -> QuerySet:
        return self.exclude(
            affiliation__beginning__lte=current_epoch_week(), affiliation__end__gte=current_epoch_week())

    def no_slack_id(self) -> QuerySet:
        return self.filter(slack_id='')

    def has_slack_id(self) -> QuerySet:
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

    def switchable_assignments_for_request(self, duty_switch):
        from_week = duty_switch.requester_assignment.cleaning_week.week  # TODO from_week should be current epoch week
        switchable_assignments = self.assignment_set.filter(cleaning_week__week__range=(from_week, from_week+12))
        requested = duty_switch.possible_acceptors()
        acceptable = switchable_assignments
        return requested & acceptable

    def can_accept_duty_switch_request(self, duty_switch):
        return len(self.switchable_assignments_for_request(duty_switch)) != 0

    def current_affiliation(self):
        try:
            current_affiliation = self.affiliation_set.get(
                beginning__lte=current_epoch_week(), end__gte=current_epoch_week()
            )
            return current_affiliation
        except Affiliation.DoesNotExist:
            return None

    def all_assignments_during_affiliation_with_schedule(self, schedule: Schedule) -> QuerySet:
        """
        Finds all Assignments that a Schedule has during the time this Cleaner is affiliated with it

        :param schedule: The Schedule object to consider
        :return: A QuerySet with Assignments
        """
        assignments_while_affiliated = Assignment.objects.none()
        for affiliation in self.affiliation_set.filter(group__schedules=schedule).all():
            assignments_while_affiliated |= Assignment.objects.filter(
                cleaning_week__week__gte=affiliation.beginning, cleaning_week__week__lte=affiliation.end,
                cleaning_week__schedule=schedule)
        return assignments_while_affiliated

    def own_assignments_during_affiliation_with_schedule(self, schedule: Schedule) -> QuerySet:
        return self.all_assignments_during_affiliation_with_schedule(schedule).filter(cleaner=self)

    def deployment_ratio_for_schedule(self, schedule) -> float:
        nr_all_assignments = self.all_assignments_during_affiliation_with_schedule(schedule).count()
        nr_own_assignments = self.own_assignments_during_affiliation_with_schedule(schedule).count()
        if nr_all_assignments != 0:
            return nr_own_assignments / nr_all_assignments
        else:
            return 0.0

    def is_active(self):
        return self.current_affiliation() is not None

    def nr_assignments_in_week(self, week: int):
        return self.assignment_set.filter(cleaning_week__week=week).count()

    def is_eligible_for_week(self, week: int):
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

    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE, editable=False)
    group = models.ForeignKey(ScheduleGroup, on_delete=models.CASCADE, null=False)

    beginning = models.IntegerField()
    end = models.IntegerField()

    objects = AffiliationQuerySet.as_manager()

    def __str__(self):
        return self.cleaner.name+" in "+self.group.name+" from week"+str(self.beginning)+" to week"+str(self.end)

    def __init__(self, *args, **kwargs):
        super(Affiliation, self).__init__(*args, **kwargs)

        if self.pk:
            self.__previous_cleaner = self.cleaner
            self.__previous_group = self.group
        else:
            self.__previous_cleaner = None
            self.__previous_group = None

    def beginning_as_date(self):
        return epoch_week_to_monday(self.beginning)

    def end_as_date(self):
        return epoch_week_to_sunday(self.end)

    @staticmethod
    def date_validator(pk, cleaner: Cleaner, beginning: int, end: int):
        if beginning > end:
            raise ValidationError("Das Ende einer Zugehörigkeit darf nicht vor dem Anfang liegen!")

        other_affiliations = cleaner.affiliation_set

        if pk:
            other_affiliations = other_affiliations.exclude(pk=pk)

        if other_affiliations.filter(beginning__range=(beginning, end)).exists():
            raise ValidationError("Der vogeschlagene Beginn dieser Zugehörigkeit überlappt "
                                  "mit einer anderen Zugehörigkeit. "
                                  "Bitte passe die andere Zugehörigkeit zuerst an, "
                                  "damit es zu keiner Überlappung kommt.")

        if other_affiliations.filter(end__range=(beginning, end)).exists():
            raise ValidationError("Das vogeschlagene Ende dieser Zugehörigkeit überlappt "
                                  "mit einer anderen Zugehörigkeit. "
                                  "Bitte passe die andere Zugehörigkeit zuerst an, "
                                  "damit es zu keiner Überlappung kommt.")

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # Does editable=False do this for us?
        # if self.__previous_cleaner:  # and self.__previous_group:
        #     if self.__previous_cleaner != self.cleaner:  # or self.__previous_group != self.group:
        #         raise ValidationError("Cleaner of an Affiliation cannot be changed!")

        self.date_validator(pk=self.pk, cleaner=self.cleaner, beginning=self.beginning, end=self.end)

        # if self.pk:
        #     # Modifying an already created object
        #     beginning_was_set_before_beginning_of_these = \
        #         self.cleaner.affiliation_set.filter(
        #             beginning__lt=self.__previous_beginning, beginning__gte=self.beginning)
        #     if beginning_was_set_before_beginning_of_these.exists():
        #         raise ValidationError("You can't set the beginning before the beginning of another Affiliation of "
        #                                "a Cleaner.")
        # else:
        #     # Creating a new object
        #     if self.cleaner.affiliation_set.filter(beginning__gte=self.beginning).exclude(pk=self.pk).exists():
        #         # The proposed Affiliation shall begin before an existing Affiliation begins -> Not allowed!
        #         # Affiliations can only be chained behind each other in time
        #         raise ValidationError("Affiliation with beginning before beginning of another Affiliation of "
        #                                "a Cleaner cannot be created!")

        super().save(force_insert, force_update, using, update_fields)

        # I don't think we should do this here. I believe the generation of Assignments should be a triggered event.
        # Because sometimes the admin wants to change many Affiliations at once which would affect each other.
        # for (previous, current) in [(self.__previous_beginning, self.beginning), (self.__previous_end, self.end)]:
        #     if not previous or previous == current:
        #         continue
        #     interval_start = min(previous, current)
        #     interval_end = max(previous, current)
        #     Assignment.objects. \
        #         filter(cleaning_week__week__gte=interval_start). \
        #         filter(cleaning_week__week__lte=interval_end). \
        #         delete()
        #     for schedule in self.group.schedules.all():
        #         schedule.new_cleaning_duties(interval_start, interval_end, 3)

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
    week = models.IntegerField(editable=False)
    excluded = models.ManyToManyField(Cleaner)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, editable=False)
    tasks_valid = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)

    objects = CleaningWeekQuerySet.as_manager()

    def __str__(self):
        return "{}: Week {}".format(self.schedule.name, self.week)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_missing_tasks(self):
        missing_task_templates = self.task_templates_missing()
        for task_template in missing_task_templates.all():
            self.task_set.create(template=task_template)
        self.tasks_valid = True
        self.save()

    def task_templates_missing(self):
        return self.schedule.tasktemplate_set.exclude(pk__in=[x.template.pk for x in self.task_set.all()])

    def has_tasks(self):
        return self.task_set.exists()

    def is_active(self):
        return self.task_set.active().exists()

    def is_passed(self):
        return self.has_tasks() and not self.task_set.in_future().exists() and not self.is_active()

    def is_in_future(self):
        return self.task_set.in_future().exists() and not self.is_active()

    def week_start(self):
        return epoch_week_to_monday(self.week)

    def week_end(self):
        return epoch_week_to_sunday(self.week)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # TODO When created, populate task_set

        # if self.date != self.__previous_date:
        #     date_difference = self.__previous_date - self.date
        #     for task in self.task_set.all():
        #         task.start_date -= date_difference
        #         task.end_date -= date_difference
        #         task.save()
        super().save(force_insert, force_update, using, update_fields)


class AssignmentQuerySet(models.QuerySet):
    def eligible_switching_destination_candidates(self, source_assignment):
        return self.filter(schedule=source_assignment.schedule).\
            filter(cleaning_week__week__gt=source_assignment.cleaning_week.week).\
            exclude(cleaning_week__excluded=source_assignment.cleaner)


class Assignment(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    cleaners_comment = models.CharField(max_length=200)
    created = models.DateField(auto_now_add=timezone.now().date(), editable=False)

    cleaning_week = models.ForeignKey(CleaningWeek, on_delete=models.CASCADE, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, editable=False)

    objects = AssignmentQuerySet.as_manager()

    class Meta:
        ordering = ('-cleaning_week__week',)

    def __str__(self):
        return "{}: {}, {} ".format(
            self.cleaning_week.schedule.name, self.cleaner.name, self.assignment_date().strftime('%d-%b-%Y'))

    def assignment_date(self):
        return epoch_week_to_monday(self.cleaning_week.week) + datetime.timedelta(days=self.schedule.weekday)

    def all_cleaners_in_week_for_schedule(self):
        return Cleaner.objects.filter(assignment__cleaning_week=self.cleaning_week)

    def other_cleaners_in_week_for_schedule(self):
        return self.all_cleaners_in_week_for_schedule().exclude(pk=self.cleaner.pk)

    def switch_requested(self):
        duty_switch = DutySwitch.objects.filter(requester_assignment=self).filter(acceptor_assignment__isnull=True)
        if duty_switch.exists():
            return duty_switch.first()
        else:
            return None


class TaskTemplateQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(disabled=False)

    def disabled(self):
        return self.filter(disabled=True)


class TaskTemplate(models.Model):
    task_name = models.CharField(max_length=20)
    task_help_text = models.CharField(max_length=200, default="", null=True)
    start_days_before = models.IntegerField(choices=[(0, ''), (1, ''), (2, ''), (3, ''), (4, ''), (5, ''), (6, '')])
    end_days_after = models.IntegerField(choices=[(0, ''), (1, ''), (2, ''), (3, ''), (4, ''), (5, ''), (6, '')])

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, editable=False)
    task_disabled = models.BooleanField(default=False)

    objects = TaskTemplateQuerySet.as_manager()

    def __str__(self):
        return self.task_name

    def start_day_to_weekday(self):
        return Schedule.WEEKDAYS[(self.schedule.weekday-self.start_days_before) % 7][1]

    def end_day_to_weekday(self):
        return Schedule.WEEKDAYS[(self.schedule.weekday+self.end_days_after) % 7][1]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.start_days_before + self.end_days_after > 6:
            raise OperationalError("The sum of start_days_before and end_days_after cannot be greater 6!")
        super().save(force_insert, force_update, using, update_fields)

        # TODO when newly created or changed, update tasks of upcoming CleaningDays


class TaskQuerySet(models.QuerySet):
    def cleaned(self):
        return self.exclude(cleaned_by__isnull=True)

    def uncleaned(self):
        return self.filter(cleaned_by__isnull=True)


class Task(models.Model):
    cleaning_week = models.ForeignKey(CleaningWeek, on_delete=models.CASCADE, editable=False)
    cleaned_by = models.ForeignKey(Cleaner, null=True, on_delete=models.PROTECT)
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, editable=False)

    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return self.template.task_name

    def start_date(self):
        return self.cleaning_week.week_start() \
               + datetime.timedelta(days=self.cleaning_week.schedule.weekday) \
               - datetime.timedelta(days=self.template.start_days_before)

    def end_date(self):
        return self.cleaning_week.week_start() \
               + datetime.timedelta(days=self.cleaning_week.schedule.weekday) \
               + datetime.timedelta(days=self.template.end_days_after)

    def possible_cleaners(self):
        return Cleaner.objects.filter(
            pk__in=[x.cleaner.pk for x in self.cleaning_week.assignment_set.all()])


class DutySwitchQuerySet(models.QuerySet):
    def open(self, schedule=None):
        if schedule:
            return self.filter(acceptor_assignment__isnull=True).filter(requester_assignment__schedule=schedule)
        else:
            return self.filter(acceptor_assignment__isnull=True)

    def closed(self, schedule=None):
        if schedule:
            return self.exclude(acceptor_assignment__isnull=True).filter(requester_assignment__schedule=schedule)
        else:
            return self.exclude(acceptor_assignment__isnull=True)


class DutySwitch(models.Model):
    class Meta:
        ordering = ('created',)
    created = models.DateField(auto_now_add=timezone.now().date())

    requester_assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="requester", editable=False)
    acceptor_assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True, related_name="acceptor")

    objects = DutySwitchQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super(DutySwitch, self).__init__(*args, **kwargs)
        self.__previous_acceptor = self.acceptor_assignment

    def __str__(self):
        if self.acceptor_assignment:
            return "Requester: {} on {}  -  Acceptor: {} on {}".\
                format(self.requester_assignment.cleaner.name,
                       self.requester_assignment.assignment_date().strftime('%d-%b-%Y'),
                       self.acceptor_assignment.cleaner.name,
                       self.acceptor_assignment.assignment_date().strftime('%d-%b-%Y'))
        else:
            return "Requester: {} on {}  -  Acceptor: none yet". \
                format(self.requester_assignment.cleaner.name,
                       self.requester_assignment.assignment_date().strftime('%d-%b-%Y'))

    def possible_acceptors(self, pk_list=None):
        candidates = Assignment.objects.eligible_switching_destination_candidates(self.requester_assignment)
        if pk_list:
            return candidates.filter(pk__in=pk_list)
        else:
            return candidates

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.__previous_acceptor is None and self.acceptor_assignment is not None:
            self.requester_assignment.cleaning_week.excluded.add(self.requester_assignment.cleaner)

            source_cleaner = self.requester_assignment.cleaner

            self.requester_assignment.cleaner = self.acceptor_assignment.cleaner
            self.requester_assignment.save()

            self.acceptor_assignment.cleaner = source_cleaner
            self.acceptor_assignment.save()

        super().save(force_insert, force_update, using, update_fields)
