from django.db import models
from django.utils import timezone
from django.core.validators import validate_comma_separated_integer_list


class CleaningPlan(models.Model):
    name = models.CharField(max_length=20)
    cleaners_per_week = models.IntegerField(default=1)
    tasks = models.CharField(max_length=200, validators=[validate_comma_separated_integer_list])


class Cleaners(models.Model):
    name = models.CharField(max_length=20)
    email = models.CharField(max_length=40)


class Config(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateField(default=timezone.now)
    cleaners = models.ManyToManyField(Cleaners)
    start_date = models.DateField()
    end_date = models.DateField()
    cleaning_plans = models.ManyToManyField(CleaningPlan)




