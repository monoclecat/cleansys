from django.db import models
from operator import itemgetter
import math
from django.utils import timezone
from django.core.validators import validate_comma_separated_integer_list

import logging


class Cleaner(models.Model):
    name = models.CharField(max_length=10)
    moved_in = models.DateField()
    moved_out = models.DateField()

    def __str__(self):
        return self.name

    def free_on_date(self, date):
        return not CleaningDuty.objects.filter(date=date, cleaners=self).exists()

    def nr_of_assigned_schedules(self):
        return CleaningSchedule.objects.filter(cleaners=self).count()


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

    def deployment_ratios(self, for_date):
        ratios = []
        for cleaner in self.cleaners.filter(moved_out__gte=for_date, moved_in__lte=for_date):

            all_duties = self.duties.filter(date__range=(cleaner.moved_in, cleaner.moved_out))
            if all_duties.exists():
                ratios.append([cleaner.pk, all_duties.filter(cleaners=cleaner).count()/all_duties.count()])
        return ratios

    def max_cleaning_ratio(self, on_date):
        nr_cleaners_on_date = self.cleaners.filter(moved_out__gte=on_date, moved_in__lte=on_date).count()
        return self.cleaners_per_date / nr_cleaners_on_date

    def new_cleaning_duty(self, date):
        """Generates a new CleaningDuty and assigns Cleaners to it.
        If self.frequency is set to 'Even weeks' and it is not an even week, this function fails silently.
        The same is true if self.frequency is set to 'Odd weeks'."""

        if self.frequency == 1 or \
                self.frequency == 2 and date.isocalendar()[1] % 2 == 0 or \
                self.frequency == 3 and date.isocalendar()[1] % 2 == 1:

            print('------------- CREATING NEW CLEANING DUTY FOR {} on the {} -------------'.format(self.name, date))

            duty, was_created = self.duties.get_or_create(date=date)
            duty.cleaners.clear()  # TODO If duty with cleaners already exists, should we prompt for approval?
            self.duties.add(duty)

            ratios = self.deployment_ratios(date)
            print('Ratios: {}'.format(ratios))

            for i in range(min(self.cleaners_per_date, self.cleaners.count())):
                print("Inserting {}. cleaner".format(i+1))
                ratios = sorted(ratios, key=itemgetter(1), reverse=False)

                modified_ratios = []
                for cleaner, ratio in ratios:
                    if Cleaner.objects.get(pk=cleaner) not in duty.cleaners.all() \
                            and ratio <= self.max_cleaning_ratio(date):
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
