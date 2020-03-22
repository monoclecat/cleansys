from django.test import TestCase
from webinterface.models import *
from django.core.exceptions import ValidationError

import logging
from unittest.mock import *


class AffiliationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.start_week = 2500
        cls.end_week = 2510

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        cls.group2 = ScheduleGroup.objects.create(name="group2")

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=1)

        # Affiliation
        cls.previous_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.start_week - 10, end=cls.start_week - 2)
        cls.affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.start_week, end=cls.end_week)
        cls.next_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.end_week + 2, end=cls.end_week + 10)

    def test__str(self):
        affil_str = str(self.affiliation)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.start_week), affil_str)
        self.assertIn(str(self.end_week), affil_str)

    def test__date_validator__end_before_beginning(self):
        self.assertRaises(ValidationError, Affiliation.date_validator,
                          self.affiliation.pk, self.cleaner1,
                          beginning=self.start_week, end=self.start_week-1)

    def test__save__end_same_as_beginning(self):
        self.assertIsNone(Affiliation.date_validator(self.affiliation.pk, self.cleaner1,
                                                     beginning=self.start_week, end=self.start_week))

    def test__save__beginning_overlaps_with_other_affiliation(self):
        self.assertRaises(ValidationError, Affiliation.date_validator,
                          self.affiliation.pk, self.cleaner1,
                          beginning=self.previous_affiliation.end, end=self.end_week)

    def test__save__end_overlaps_with_other_affiliation(self):
        self.assertRaises(ValidationError, Affiliation.date_validator,
                          self.affiliation.pk, self.cleaner1,
                          beginning=self.start_week, end=self.next_affiliation.beginning)

    def test__beginning_as_date(self):
        self.assertEqual(self.affiliation.beginning_as_date(), epoch_week_to_monday(self.start_week))

    def test__end_as_date(self):
        self.assertEqual(self.affiliation.end_as_date(), epoch_week_to_sunday(self.end_week))
