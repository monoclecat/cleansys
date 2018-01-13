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

    def paginated_duties(self):
        page_size = 25
        start_from = datetime.datetime.now().date() - datetime.timedelta(days=3)
        duties = CleaningDuty.objects.filter(date__gte=correct_dates_to_weekday(start_from, 6))


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


class CleaningDuty(models.Model):
    cleaners = models.ManyToManyField(Cleaner)
    date = models.DateField()
    excluded = models.ManyToManyField(Cleaner, related_name="excluded")

    tasks = models.CharField(max_length=200, null=True)
    # String representation of a list of lists:[<task name>, <cleaner pk that finished task>]
    # tasks is only filled when an assigned cleaner presses the "Lass putzen" button, initiating the cleaning process
    # <cleaner pk that finished task> stays empty until a cleaner assigned on that date says he finished that task
    # String representation: <task_name>,<cleaner pk that finished task>;<task_name,...

    def __str__(self):
        string = ""
        for cleaner in self.cleaners.all():
            string += cleaner.name + ", "
        return string[:-2]

    def get_tasks(self):
        """Parses destinations field into a list and
        returns [wish destination pair], [[list of following destinations]]"""
        task_list = []
        if self.tasks:
            for pair in self.tasks.split(";"):
                task_name, cleaner_pk = pair.split(",")
                try:
                    if cleaner_pk:
                        cleaner = Cleaner.objects.get(pk=cleaner_pk)
                    else:
                        cleaner = None

                    task_list.append([task_name, cleaner])
                except Cleaner.DoesNotExist:
                    pass
        return task_list

    def set_tasks(self, task_list):
        task_string = ""
        for task_name, cleaner in task_list:
            task_string += task_name + ","
            if cleaner is not None:
                task_string += str(cleaner.pk)
            task_string += ";"
        task_string = task_string[:-1]
        self.tasks = task_string

    def task_completed(self, completed_task_name, by_cleaner):
        if by_cleaner not in self.cleaners.all():
            return False

        completed_task_name_exists = False
        new_tasks = ""
        for task_name, cleaner in self.get_tasks():
            if task_name == completed_task_name:
                cleaner = by_cleaner
                completed_task_name_exists = True
            new_tasks += task_name + ","
            if cleaner:
                new_tasks += str(cleaner.pk)
            new_tasks += ";"

        if not completed_task_name_exists:
            return False

        new_tasks = new_tasks[:-1]
        self.tasks = new_tasks
        return True

    def initiate_tasks(self):
        task_string = ""
        task_list = self.cleaningschedule_set.first().get_tasks()
        if not task_list == ['']:
            for task_name in task_list:
                task_string += task_name + ",;"
            task_string = task_string[:-1]
            self.tasks = task_string


class CleaningScheduleGroup(models.Model):
    class Meta:
        ordering = ("name", )
    name = models.CharField(max_length=30, unique=True)
    cleaners = models.ManyToManyField(Cleaner)

    def __str__(self):
        return self.name


class CleaningSchedule(models.Model):
    name = models.CharField(max_length=20, unique=True)

    CLEANERS_PER_DATE_CHOICES = ((1, 'Einen'), (2, 'Zwei'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Jede Woche'), (2, 'Gerade Wochen'), (3, 'Ungerade Wochen'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

    duties = models.ManyToManyField(CleaningDuty, blank=True)
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
        super(CleaningSchedule, self).save(force_insert, force_update, using, update_fields)

        if self.cleaners_per_date != self.__last_cleaners_per_date or self.frequency != self.__last_frequency:
            all_duty_dates = list(self.duties.values_list('date', flat=True))
            self.duties.all().delete()
            for date in all_duty_dates:
                self.assign_cleaning_duty(date)

    def delete(self, using=None, keep_parents=False):
        for duty in self.duties.all():
            duty.delete()
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
                all_duties = self.duties.filter(date__range=(cleaner.moved_in, cleaner.moved_out))
                if all_duties.exists():
                    proportion__all_duties_he_cleans = all_duties.filter(cleaners=cleaner).count() / all_duties.count()
                    ratios.append([cleaner,
                                   proportion__all_duties_he_cleans / proportion__cleaners_assigned_per_week])
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
            self.duties.filter(date__range=(start_date, end_date)).delete()

        date_iterator = start_date
        while date_iterator <= end_date:
            if clear_existing or not clear_existing and not self.duties.filter(date=date_iterator).exists():
                self.assign_cleaning_duty(date_iterator)
            date_iterator += one_week

    def assign_cleaning_duty(self, date):
        """Generates a new CleaningDuty and assigns Cleaners to it.
        If self.frequency is set to 'Even weeks' and it is not an even week, this function fails silently.
        The same is true if self.frequency is set to 'Odd weeks'."""

        if self.defined_on_date(date):

            duty, was_created = self.duties.get_or_create(date=date)

            duty.cleaners.clear()
            self.duties.add(duty)

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
                        if cleaner not in duty.cleaners.all() and cleaner not in duty.excluded.all():
                            if cleaner.cleaningduty_set.filter(date=date).count() == 0:
                                duty.cleaners.add(cleaner)
                                logging.debug("          {} inserted!".format(cleaner.name))
                                break
                            elif not last_resort_cleaner and cleaner.cleaningduty_set.filter(date=date).count() == 1:
                                last_resort_cleaner = cleaner
                            logging.debug("{} is not free.".format(cleaner.name))
                    else:
                        if last_resort_cleaner:
                            logging.debug("Nobody has 0 duties on date so we choose {}".format(last_resort_cleaner))
                            duty.cleaners.add(last_resort_cleaner)
                        else:
                            logging.debug("NOBODY HAS 1 DUTY ON DATE! We choose {}".format(ratios[0][0]))
                            duty.cleaners.add(ratios[0][0])

            logging.debug("")


def group_cleaners_changed(instance, action, pk_set, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        dates_to_delete = []
        one_week = datetime.timedelta(days=7)
        for cleaner_pk in pk_set:
            cleaner = Cleaner.objects.get(pk=cleaner_pk)
            first_duty, last_duty = correct_dates_to_weekday([min(cleaner.moved_in, datetime.datetime.now().date()),
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
    source_cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    source_duty = models.ForeignKey(CleaningDuty, on_delete=models.CASCADE)

    selected_cleaner = models.ForeignKey(Cleaner, on_delete=models.SET_NULL, null=True, related_name="selected_cleaner")
    selected_duty = models.ForeignKey(CleaningDuty, on_delete=models.SET_NULL, null=True, related_name="selected_duty")

    destinations = models.CharField(max_length=100, null=True)
    # destinations is a string representation of a list of lists [<cleanerpk>, <dutypk>] which are suitable candidates
    # for the source to switch with. Example: <cleanerpk>,<dutypk>;<cleanerpk>,<dutypk>;<cleanerpk>,<dutypk>
    # destinations is a FIFO type stack, the wish destination is always the first pair of PKs

    STATES = ((0, 'Waiting on source choice'), (1, 'Waiting on approval for selected'), (2, 'Selected was rejected'))
    status = models.IntegerField(choices=STATES, default=0)
    # DutySwitch object gets created in statue 0 as Cleaner needs to select a desired Duty destination.
    # When the desired Duty is selected the status is set to 1 because we need approval
    # from the destination to commence switching.
    # If the destination denies approval, status is set to 2 because the source needs to select a new
    # destination. The cycle begins from the start

    def get_destinations(self):
        """Parses destinations field into a list and
        returns [wish destination pair], [[list of following destinations]]"""
        dest_list = []
        for pair in self.destinations.split(";"):
            cleaner_pk, duty_pk = pair.split(",")
            try:
                dest_list.append([Cleaner.objects.get(pk=cleaner_pk), CleaningDuty.objects.get(pk=duty_pk)])
            except (Cleaner.DoesNotExist, CleaningDuty.DoesNotExist):
                pass
        return dest_list

    def set_selected(self, cleaner, duty):
        self.selected_cleaner = cleaner
        self.selected_duty = duty
        self.status = 1

    def set_destinations(self, dest_list):
        dest_string = ""
        for cleaner_pk, duty_pk in dest_list:
            dest_string += str(cleaner_pk) + "," + str(duty_pk)
            dest_string += ";"
        dest_string = dest_string[:-1]
        return dest_string

    def selected_was_accepted(self):
        self.source_duty.excluded.add(self.source_cleaner)
        self.source_duty.cleaners.remove(self.source_cleaner)
        self.source_duty.cleaners.add(self.selected_cleaner)

        self.selected_duty.cleaners.remove(self.selected_cleaner)
        self.selected_duty.cleaners.add(self.source_cleaner)

        confirmation_text = "Dein Tausch war erfolgreich!"
        # TODO send confirmation to source and destination

        self.delete()

    def selected_was_cancelled(self):
        self.selected_duty = None
        self.selected_cleaner = None
        self.status = 0

    def selected_was_rejected(self):
        old_dest = self.get_destinations()
        new_dest = []
        for dest_cleaner, dest_duty in old_dest:
            if not self.selected_cleaner.pk == dest_cleaner.pk and not self.selected_duty.pk == dest_duty.pk:
                new_dest.append([dest_cleaner.pk, dest_duty.pk])
        self.set_destinations(new_dest)

        self.selected_duty = None
        self.selected_cleaner = None
        self.status = 2

        confirmation_text = "Die Anfrage wurde erfolgreich abgelehnt"
        new_options_text = "Deine Anfrage wurde abgeleht. Wähle bitte eine der weiteren Optionen"

        # TODO send message to source with new options and confirmation to destination

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.destinations:
            duty = self.source_duty
            schedule = duty.cleaningschedule_set.first()

            ratios = schedule.deployment_ratios(duty.date)
            logging.debug("------------ Looking for replacement cleaners -----------")
            free_cleaners = []
            one_duty_cleaners = []
            for cleaner, ratio in ratios:
                logging.debug(
                    "{}:   Not in duty:{} Duties today:{}".format(cleaner.name, cleaner not in duty.cleaners.all(),
                                                                             cleaner.cleaningduty_set.filter(
                                                                                 date=duty.date).count()))
                if cleaner not in duty.cleaners.all():
                    if cleaner.cleaningduty_set.filter(date=duty.date).count() == 0:
                        free_cleaners.append(cleaner)
                    elif cleaner.cleaningduty_set.filter(date=duty.date).count() == 1:
                        one_duty_cleaners.append(cleaner)

            if free_cleaners:
                replacement_cleaners = free_cleaners
            else:
                replacement_cleaners = one_duty_cleaners

            if len(replacement_cleaners) >= 3:
                replacement_cleaners = replacement_cleaners[:3]

            logging.debug("Replacement cleaners: {}".format(replacement_cleaners))

            replacement_duties = []
            for cleaner in replacement_cleaners:
                duties = schedule.duties.filter(cleaners=cleaner, date__gt=duty.date).order_by('date')
                if duties.count() >= 2:
                    duties = duties[:2]
                for repl_duty in duties:
                    replacement_duties.append([cleaner.pk, repl_duty.pk])

            self.destinations = self.set_destinations(replacement_duties)

        super().save(force_insert, force_update, using, update_fields)

