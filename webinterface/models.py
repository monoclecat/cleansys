from django.db import models
from operator import itemgetter
from django.utils import timezone
from django.core.validators import validate_comma_separated_integer_list

import logging


class Cleaner(models.Model):
    name = models.CharField(max_length=10)
    moved_in = models.DateField()
    moved_out = models.DateField(null=True)

    def __str__(self):
        return self.name

    def free_on_date(self, date):
        return not CleaningDuty.objects.filter(date=date, cleaners=self).exists()

    def nr_of_assigned_schedules(self):
        return CleaningSchedule.objects.filter(cleaners=self).count()


class CleaningDuty(models.Model):
    cleaners = models.ManyToManyField(Cleaner)
    date = models.DateField()


class CleaningSchedule(models.Model):
    name = models.CharField(max_length=20)

    CLEANERS_PER_DATE_CHOICES = ((1, 'One'), (2, 'Two'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Every week'), (2, 'Even weeks'), (3, 'Odd weeks'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

    duties = models.ManyToManyField(CleaningDuty, blank=True)
    cleaners = models.ManyToManyField(Cleaner)

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

    def deployment_ratios(self, up_to_date):
        ratios = []
        for cleaner in self.cleaners.all().filter(moved_out__gte=up_to_date, moved_in__lte=up_to_date):
            weeks_living = (up_to_date - cleaner.moved_in).days // 7
            times_cleaned = CleaningDuty.objects.filter(cleaners=cleaner).count()
            ratios.append([cleaner.pk, times_cleaned/weeks_living])
        return ratios

    def new_cleaning_duty(self, date):
        ratios = self.deployment_ratios(date)

        if not CleaningDuty.objects.filter(date=date).exists():
            duty = CleaningDuty.objects.create(date=date)
            for i in range(min(self.cleaners_per_date, self.cleaners.count())):
                ratios = sorted(ratios, key=itemgetter(1), reverse=False)
                for cleaner, ratio in ratios:
                    if cleaner.free_on_date(date):
                        duty.cleaners.add()
                        break
                else:
                    duty.cleaners.add(ratios[0][0])
