from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class CleaningWeekQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_week1 = 2500
        cls.reference_week2 = 2501
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.enabled = CleaningWeek.objects.create(week=cls.reference_week1, schedule=cls.schedule, disabled=False)
        cls.disabled = CleaningWeek.objects.create(week=cls.reference_week2, schedule=cls.schedule, disabled=True)

    def test__enabled(self):
        enabled_schedules = CleaningWeek.objects.enabled()
        self.assertIn(self.enabled, enabled_schedules)
        self.assertNotIn(self.disabled, enabled_schedules)

    def test__disabled(self):
        disabled_schedules = CleaningWeek.objects.disabled()
        self.assertIn(self.disabled, disabled_schedules)
        self.assertNotIn(self.enabled, disabled_schedules)


# class CleaningWeekTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.reference_week = 2500
#         cls.schedule = Schedule.objects.create(name="schedule")
#         cls.cleaning_day = CleaningWeek.objects.create(week=cls.reference_week, schedule=cls.schedule)
#         cls.task1 = TaskTemplate.objects.create(
#             name="tasktemplate1", schedule=cls.schedule, start_days_before=1, end_days_after=2)
#         cls.task2 = TaskTemplate.objects.create(
#             name="tasktemplate2", schedule=cls.schedule, start_days_before=1, end_days_after=2)
#         cls.cleaner = Cleaner.objects.create(name="cleaner")
#         cls.assignment = Assignment.objects.create(
#             cleaner=cls.cleaner, schedule=cls.schedule, cleaning_day=cls.cleaning_day)
#
#     def test__str(self):
#         self.assertIn(self.schedule.name, self.cleaning_day.__str__())
#         self.assertIn(self.cleaning_day.date.strftime('%d-%b-%Y'), self.cleaning_day.__str__())
