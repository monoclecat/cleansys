from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class TaskTemplateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.week = 2500
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.schedule2 = Schedule.objects.create(name="schedule2")
        cls.cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week,
                                                        tasks_valid=True)
        cls.cleaning_week2 = CleaningWeek.objects.create(schedule=cls.schedule2, week=cls.week + 1,
                                                         tasks_valid=True)
        cls.future_cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week + 1,
                                                               tasks_valid=True)
        cls.task_template = TaskTemplate.objects.create(schedule=cls.schedule, start_days_before=1, end_days_after=1)

    def test__str(self):
        self.assertEqual(self.task_template.__str__(), self.task_template.task_name)

    def test__start_day_to_weekday(self):
        self.assertEqual(self.task_template.start_day_to_weekday(), Schedule.WEEKDAYS[1][1])

    def test__end_day_to_weekday(self):
        self.assertEqual(self.task_template.end_day_to_weekday(), Schedule.WEEKDAYS[3][1])
