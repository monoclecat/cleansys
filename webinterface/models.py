from django.db import models
from operator import itemgetter
import datetime
import math
from django.utils import timezone
from django.core.validators import validate_comma_separated_integer_list

import logging


def correct_dates_to_weekday(days, weekday):
    """Days is a date or list of datetime.date objects you want converted. 0 = Monday, 6 = Sunday"""
    if isinstance(days, list):
        corrected_days = []
        for day in days:
            day += datetime.timedelta(days=weekday - day.weekday())
            corrected_days.append(day)
        return corrected_days
    if isinstance(days, datetime.date):
        return days + datetime.timedelta(days=weekday - days.weekday())


class Cleaner(models.Model):
    name = models.CharField(max_length=10)
    moved_in = models.DateField()
    moved_out = models.DateField()

    # TODO Cleaners can't just be deleted, first their associations to Schedules must be broken!

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

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)

        associated_schedules = CleaningSchedule.objects.filter(cleaners=self)

        if self.moved_out != self.__last_moved_out:
            prev_last_duty, new_last_duty = correct_dates_to_weekday([self.__last_moved_out, self.moved_out], 6)
            if prev_last_duty != new_last_duty:
                for schedule in associated_schedules:
                    schedule.new_cleaning_duties(prev_last_duty, new_last_duty, False)

        if self.moved_in != self.__last_moved_in:
            prev_first_duty, new_first_duty = correct_dates_to_weekday([self.__last_moved_in, self.moved_in], 6)
            if prev_first_duty != new_first_duty:
                for schedule in associated_schedules:
                    schedule.new_cleaning_duties(prev_first_duty, new_first_duty, False)

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

    def __init__(self, *args, **kwargs):
        super(CleaningSchedule, self).__init__(*args, **kwargs)
        self.__last_cleaners = self.cleaners.values_list('pk', flat=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)

        # TODO test this

        cleaners_list_prev = self.cleaners.values_list('pk', flat=True)
        cleaners_list_now = self.__last_cleaners
        new_cleaners = []
        deleted_cleaners = []
        for prev_cleaner_pk in cleaners_list_prev:
            if prev_cleaner_pk not in cleaners_list_now:
                deleted_cleaners.append(prev_cleaner_pk)
        for now_cleaner_pk in cleaners_list_now:
            if now_cleaner_pk not in cleaners_list_prev:
                new_cleaners.append(now_cleaner_pk)

        dates_to_redistribute = []
        one_week = datetime.timedelta(days=7)
        for cleaner in new_cleaners + deleted_cleaners:
            first_duty, last_duty = correct_dates_to_weekday([cleaner.moved_in, cleaner.moved_out], 6)
            date_iterator = first_duty
            while date_iterator <= last_duty:
                if date_iterator not in dates_to_redistribute:
                    dates_to_redistribute.append(date_iterator)
                    date_iterator += one_week

        dates_to_redistribute = sorted(dates_to_redistribute)
        for date in dates_to_redistribute:
            self.duties.filter(date=date).delete()
        for date in dates_to_redistribute:
            self.new_cleaning_duty(date, False)

        self.__last_cleaners = self.cleaners.values_list('pk', flat=True)

    def delete(self, using=None, keep_parents=False):
        for duty in self.duties.all():
            duty.delete()
        super().delete(using, keep_parents)

    def deployment_ratios(self, for_date=None, for_date_range=None):
        """Returns <number of duties a cleaner cleans in>/<total number of duties while cleaner lives in house>
        for either
        1)for_date: All cleaners that live in house on a particular date
        2)for_date_range=(date1, date2): All cleaners that live in house on one or more of the dates in range"""
        ratios = []
        if for_date:
            active_cleaners_on_date = self.cleaners.filter(moved_out__gte=for_date, moved_in__lte=for_date)
            for cleaner in active_cleaners_on_date:

                all_duties = self.duties.filter(date__range=(cleaner.moved_in, cleaner.moved_out))
                proportion__all_duties_he_cleans = all_duties.filter(cleaners=cleaner).count()/all_duties.count()

                proportion__cleaners_assigned_per_week = active_cleaners_on_date.count()/self.cleaners_per_date
                if all_duties.exists():
                    ratios.append([cleaner.pk,
                                   proportion__all_duties_he_cleans * proportion__cleaners_assigned_per_week])
            return sorted(ratios, key=itemgetter(1), reverse=False)
        elif for_date_range:
            date1, date2 = for_date_range
            start_date = min(date1, date2)
            end_date = max(date1, date2)

            for cleaner in self.cleaners.filter(moved_out__gte=start_date, moved_in__lte=end_date):

                active_cleaners = self.cleaners.filter(moved_out__gte=min(cleaner.moved_out, end_date),
                                                       moved_in__lte=min(cleaner.moved_out, end_date))
                all_duties = self.duties.filter(date__range=(cleaner.moved_in, cleaner.moved_out))
                proportion__all_duties_he_cleans = all_duties.filter(cleaners=cleaner).count() / all_duties.count()

                proportion__cleaners_assigned_per_week = active_cleaners.count() / self.cleaners_per_date
                if all_duties.exists():
                    ratios.append([cleaner.pk,
                                   proportion__all_duties_he_cleans * proportion__cleaners_assigned_per_week])
            return sorted(ratios, key=itemgetter(1), reverse=False)

    def new_cleaning_duties(self, date1, date2, create_new=True):
        """Generates new cleaning duties between date1 and date2. To ensure better distribution of cleaners,
        the cleaners of all duties in time frame are cleared."""
        start_date = min(date1, date2)
        end_date = max(date1, date2)
        one_week = datetime.timedelta(days=7)

        clear_cleaners_on_these = self.duties.filter(date__range=(start_date, end_date))
        for duty in clear_cleaners_on_these:
            duty.cleaners.clear()

        date_iterator = start_date
        while date_iterator <= end_date:
            self.new_cleaning_duty(date_iterator, create_new)
            date_iterator += one_week

    def new_cleaning_duty(self, date, create_new=True):
        """Generates a new CleaningDuty and assigns Cleaners to it.
        If self.frequency is set to 'Even weeks' and it is not an even week, this function fails silently.
        The same is true if self.frequency is set to 'Odd weeks'."""

        if self.frequency == 1 or \
                self.frequency == 2 and date.isocalendar()[1] % 2 == 0 or \
                self.frequency == 3 and date.isocalendar()[1] % 2 == 1:

            if create_new:
                duty, was_created = self.duties.get_or_create(date=date)
            else:
                duty_on_date = self.duties.filter(date=date)
                if duty_on_date.exists():
                    duty = duty_on_date.first()
                else:
                    return

            duty.cleaners.clear()  # TODO If duty with cleaners already exists, should we prompt for approval?
            self.duties.add(duty)

            ratios = self.deployment_ratios(for_date=date)
            print('------------- CREATING NEW CLEANING DUTY FOR {} on the {} -------------'.format(self.name, date))
            print("Cleaners' ratios: ")
            for cleaner, ratio in ratios:
                print("{}:{}".format(Cleaner.objects.get(pk=cleaner).name, round(ratio, 3)), end=" ")
            print("")

            for i in range(min(self.cleaners_per_date, self.cleaners.count())):
                print("Inserting {}. cleaner".format(i+1))

                modified_ratios = []
                for cleaner, ratio in ratios:
                    if Cleaner.objects.get(pk=cleaner) not in duty.cleaners.all() \
                            and ratio <= 1:
                        modified_ratios.append([cleaner, ratio])

                for cleaner, ratio in modified_ratios:
                    print("     Considering {}".format(Cleaner.objects.get(pk=cleaner).name), end=": ")
                    if Cleaner.objects.get(pk=cleaner).free_on_date(date):
                        duty.cleaners.add(Cleaner.objects.get(pk=cleaner))
                        print("Inserted!")
                        break
                    else:
                        print("Is not free.")
                else:
                    print("     All are busy, we choose {}".format(Cleaner.objects.get(pk=modified_ratios[0][0])))
                    duty.cleaners.add(Cleaner.objects.get(pk=modified_ratios[0][0]))
            print("")
