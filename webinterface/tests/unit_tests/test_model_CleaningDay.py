from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class CleaningDayQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_date1 = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.reference_date2 = correct_dates_to_due_day(datetime.date(2010, 1, 14))
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.enabled = CleaningDay.objects.create(date=cls.reference_date1, schedule=cls.schedule, disabled=False)
        cls.disabled = CleaningDay.objects.create(date=cls.reference_date2, schedule=cls.schedule, disabled=True)

    def test__enabled(self):
        enabled_schedules = CleaningDay.objects.enabled()
        self.assertIn(self.enabled, enabled_schedules)
        self.assertNotIn(self.disabled, enabled_schedules)

    def test__disabled(self):
        disabled_schedules = CleaningDay.objects.disabled()
        self.assertIn(self.disabled, disabled_schedules)
        self.assertNotIn(self.enabled, disabled_schedules)


class CleaningDayTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.cleaning_day = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.task1 = TaskTemplate.objects.create(
            name="tasktemplate1", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.task2 = TaskTemplate.objects.create(
            name="tasktemplate2", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.cleaner = Cleaner.objects.create(name="cleaner")
        cls.assignment = Assignment.objects.create(
            cleaner=cls.cleaner, schedule=cls.schedule, cleaning_day=cls.cleaning_day)

    def test__creation(self):
        cleaning_day = CleaningDay.objects.create(date=datetime.date(2010, 2, 8), schedule=self.schedule)
        self.assertIsInstance(cleaning_day, CleaningDay)

    def test__str(self):
        self.assertIn(self.schedule.name, self.cleaning_day.__str__())
        self.assertIn(self.cleaning_day.date.strftime('%d-%b-%Y'), self.cleaning_day.__str__())
