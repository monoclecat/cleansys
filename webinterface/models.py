from django.db import models
from django.utils import timezone
from django.core.validators import validate_comma_separated_integer_list

import logging


class CleaningSchedule(models.Model):
    name = models.CharField(max_length=20, unique=True)

    CLEANERS_PER_DATE_CHOICES = ((1, 'One'), (2, 'Two'))
    cleaners_per_date = models.IntegerField(default=1, choices=CLEANERS_PER_DATE_CHOICES)

    FREQUENCY_CHOICES = ((1, 'Every week'), (2, 'Even weeks'), (3, 'Odd weeks'))
    frequency = models.IntegerField(default=1, choices=FREQUENCY_CHOICES)

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


class Cleaner(models.Model):
    name = models.CharField(max_length=10, unique=True)
    assigned_to = models.ManyToManyField(CleaningSchedule)

    def free_on_date(self, date):
        return not CleaningDuty.objects.filter(date=date, cleaners=self).exists()

    def __str__(self):
        return self.name


class CleaningDuty(models.Model):
    class Meta:
        unique_together = ("date", "schedule")
    cleaners = models.ManyToManyField(Cleaner)
    date = models.DateField()
    schedule = models.ForeignKey(CleaningSchedule, null=True)

    def cleaners_missing(self):
        return self.schedule.cleaners_per_date - self.cleaners.count()

    def __str__(self):
        return str(self.schedule.name)+' '+str(self.date)

