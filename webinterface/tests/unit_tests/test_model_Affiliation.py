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

    def setUp(self) -> None:
        # Affiliation
        self.previous_affiliation = Affiliation.objects.create(
            cleaner=self.cleaner1, group=self.group, beginning=self.start_week - 10, end=self.start_week - 2)
        self.affiliation = Affiliation.objects.create(
            cleaner=self.cleaner1, group=self.group, beginning=self.start_week, end=self.end_week)
        self.next_affiliation = Affiliation.objects.create(
            cleaner=self.cleaner1, group=self.group, beginning=self.end_week + 2, end=self.end_week + 10)

    def test__str(self):
        affil_str = str(self.affiliation)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.start_week), affil_str)
        self.assertIn(str(self.end_week), affil_str)

    def test__save__end_before_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.end = affiliation.beginning - 1
        self.assertRaises(ValidationError, affiliation.save)

    def test__save__end_same_as_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.end = affiliation.beginning
        affiliation.save()  # Must not raise exception
        self.assertEqual(Affiliation.objects.get(pk=self.affiliation.pk).beginning,
                         Affiliation.objects.get(pk=self.affiliation.pk).end)

    def test__save__beginning_overlaps_with_other_affiliation(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.beginning = self.previous_affiliation.end
        self.assertRaises(ValidationError, affiliation.save)

    def test__save__end_overlaps_with_other_affiliation(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.end = self.next_affiliation.beginning
        self.assertRaises(ValidationError, affiliation.save)
