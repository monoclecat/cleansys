from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class AssignmentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        one_week = timezone.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1")
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2")
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_day1 = CleaningWeek.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.cleaning_day2 = CleaningWeek.objects.create(date=cls.reference_date + one_week, schedule=cls.schedule)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)

        # DutySwitch
        cls.dutyswitch = DutySwitch.objects.create(source_assignment=cls.assignment1)

    def test__creation(self):
        assignment = Assignment.objects.create(cleaner=self.cleaner1, schedule=self.schedule,
                                               cleaning_day=self.cleaning_day1)
        self.assertIsInstance(assignment, Assignment)

    def test__str(self):
        self.assertIn(self.schedule.name, self.assignment1.__str__())
        self.assertIn(self.cleaner1.name, self.assignment1.__str__())
        self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), self.assignment1.__str__())

    def test__cleaners_on_day_for_schedule(self):
        cleaners_on_date_for_schedule = self.assignment1.cleaners_on_date_for_schedule()
        self.assertIn(self.cleaner1, cleaners_on_date_for_schedule)
        self.assertIn(self.cleaner2, cleaners_on_date_for_schedule)
        self.assertNotIn(self.cleaner3, cleaners_on_date_for_schedule)

    def test__cleaning_buddies(self):
        cleaners_on_date_for_schedule = self.assignment1.cleaning_buddies()
        self.assertNotIn(self.cleaner1, cleaners_on_date_for_schedule)
        self.assertIn(self.cleaner2, cleaners_on_date_for_schedule)
        self.assertNotIn(self.cleaner3, cleaners_on_date_for_schedule)

    def test__is_source_of_dutyswitch(self):
        self.assertEqual(self.assignment1.is_source_of_dutyswitch(), self.dutyswitch)
        self.assertEqual(self.assignment2.is_source_of_dutyswitch(), None)
