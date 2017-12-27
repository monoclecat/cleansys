from django.db import models
from operator import itemgetter
import datetime
from django.db.models.signals import m2m_changed

import logging
import random


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
    name = models.CharField(max_length=10)
    moved_in = models.DateField()
    moved_out = models.DateField()

    def __init__(self, *args, **kwargs):
        super(Cleaner, self).__init__(*args, **kwargs)
        self.__last_moved_in = self.moved_in
        self.__last_moved_out = self.moved_out

    def __str__(self):
        return self.name

    def free_on_date(self, date):
        return not CleaningDuty.objects.filter(date=date, cleaners=self).exists()

    def nr_of_assigned_schedules(self):
        return CleaningSchedule.objects.filter(cleaners=self).count()

    def delete(self, using=None, keep_parents=False):
        associated_schedules = CleaningSchedule.objects.filter(cleaners=self)
        for schedule in associated_schedules:
            schedule.cleaners.remove(self)

        super().delete(using, keep_parents)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)

        associated_schedules = CleaningSchedule.objects.filter(cleaners=self)

        if associated_schedules:
            if self.moved_out != self.__last_moved_out:
                prev_last_duty, new_last_duty = correct_dates_to_weekday([self.__last_moved_out, self.moved_out], 6)
                if prev_last_duty != new_last_duty:
                    for schedule in associated_schedules:
                        schedule.new_cleaning_duties(prev_last_duty, new_last_duty, True)

            if self.moved_in != self.__last_moved_in:
                prev_first_duty, new_first_duty = correct_dates_to_weekday([self.__last_moved_in, self.moved_in], 6)
                if prev_first_duty != new_first_duty:
                    for schedule in associated_schedules:
                        schedule.new_cleaning_duties(prev_first_duty, new_first_duty, True)

        self.__last_moved_in = self.moved_in
        self.__last_moved_out = self.moved_out


class CleaningDuty(models.Model):
    cleaners = models.ManyToManyField(Cleaner)
    date = models.DateField()

    def __str__(self):
        string = ""
        for cleaner in self.cleaners.all():
            string += cleaner.name + " "
        return string[:-1]


class CleaningSchedule(models.Model):
    name = models.CharField(max_length=20)

    CLEANERS_PER_DATE_CHOICES = ((1, 'One'), (2, 'Two'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Every week'), (2, 'Even weeks'), (3, 'Odd weeks'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

    duties = models.ManyToManyField(CleaningDuty, blank=True)
    cleaners = models.ManyToManyField(Cleaner, blank=True)

    task1 = models.CharField(max_length=40, blank=True)
    task2 = models.CharField(max_length=40, blank=True)
    task3 = models.CharField(max_length=40, blank=True)
    task4 = models.CharField(max_length=40, blank=True)
    task5 = models.CharField(max_length=40, blank=True)
    task6 = models.CharField(max_length=40, blank=True)
    task7 = models.CharField(max_length=40, blank=True)
    task8 = models.CharField(max_length=40, blank=True)
    task9 = models.CharField(max_length=40, blank=True)
    task10 = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return self.name

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

        active_cleaners_on_date = self.cleaners.filter(moved_out__gte=for_date, moved_in__lte=for_date)
        if active_cleaners_on_date.exists():
            proportion__cleaners_assigned_per_week = self.cleaners_per_date / active_cleaners_on_date.count()

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

            if ratios:
                for i in range(min(self.cleaners_per_date, self.cleaners.count())):
                    for cleaner, ratio in ratios:
                        if cleaner not in duty.cleaners.all():
                            if cleaner.free_on_date(date):
                                duty.cleaners.add(cleaner)
                                logging.debug("          {} inserted!".format(cleaner.name))
                                break
                            logging.debug("{} is not free.".format(cleaner.name))
                    else:
                        for cleaner, ratio in ratios:
                            if cleaner not in duty.cleaners.all() and \
                                    CleaningDuty.objects.filter(date=date, cleaners=cleaner).count() <= 2:
                                logging.debug("Nobody is free, we choose {}".format(cleaner))
                                duty.cleaners.add(cleaner)
                                break
            logging.debug("")


def schedule_cleaners_changed(instance, action, pk_set, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        dates_to_delete = []
        one_week = datetime.timedelta(days=7)
        for cleaner_pk in pk_set:
            cleaner = Cleaner.objects.get(pk=cleaner_pk)
            first_duty, last_duty = correct_dates_to_weekday([cleaner.moved_in, cleaner.moved_out], 6)
            date_iterator = first_duty
            while date_iterator <= last_duty:
                if date_iterator not in dates_to_delete:
                    dates_to_delete.append(date_iterator)
                    date_iterator += one_week

        dates_to_redistribute = []
        for date in dates_to_delete:
            duty = instance.duties.filter(date=date)
            if duty.exists():
                duty.delete()
                dates_to_redistribute.append(date)
        for date in dates_to_redistribute:
            instance.assign_cleaning_duty(date)


m2m_changed.connect(schedule_cleaners_changed, sender=CleaningSchedule.cleaners.through)
