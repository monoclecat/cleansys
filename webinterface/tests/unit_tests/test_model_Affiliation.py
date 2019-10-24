from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class AffiliationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.beginning_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.one_week = timezone.timedelta(days=7)
        cls.end_date = cls.beginning_date + 4*cls.one_week

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)

        # Affiliation
        cls.prev_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.beginning_date-4*cls.one_week, end=cls.beginning_date)
        cls.affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.beginning_date, end=cls.end_date)
        cls.next_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.end_date, end=cls.end_date+4*cls.one_week)

    def test__creation(self):
        affiliation = Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                                 beginning=datetime.date(2011, 1, 1))
        self.assertIsInstance(affiliation, Affiliation)

    def test__str(self):
        affiliation = Affiliation(cleaner=self.cleaner1, group=self.group, beginning=self.beginning_date,
                                  end=self.end_date)
        affil_str = str(affiliation)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.beginning_date), affil_str)
        self.assertIn(str(self.end_date), affil_str)

    def test__str__no_end(self):
        affiliation_no_end = Affiliation(cleaner=self.cleaner1, group=self.group, beginning=self.beginning_date)
        affil_str = str(affiliation_no_end)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.beginning_date), affil_str)

    def test__delete(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            affiliation = Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                                     beginning=datetime.date(2011, 1, 1), end=datetime.date(2011, 2, 1))
            affiliation.delete()
            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(datetime.date(2011, 1, 1), datetime.date(2011, 2, 1), 3)])

    def test__save__end_before_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.end = affiliation.beginning - self.one_week
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__group_change(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.group = ScheduleGroup(name="temp")
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__cleaner_change(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.cleaner = Cleaner(name="temp")
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__set_beginning_before_other_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.beginning = self.prev_affiliation.beginning - self.one_week
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__create_with_beginning_before_other_beginning(self):
        with self.assertRaises(OperationalError):
            Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                       beginning=self.next_affiliation.beginning - self.one_week)

    def test__save__beginning_changes(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            __prev_affiliation_dates = [self.prev_affiliation.beginning, self.prev_affiliation.end]
            __next_affiliation_dates = [self.next_affiliation.beginning, self.next_affiliation.end]

            affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
            affiliation.beginning = affiliation.beginning-self.one_week
            affiliation.save()

            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(self.beginning_date - self.one_week, self.beginning_date, 3)])

            prev_affiliation = Affiliation.objects.get(pk=self.prev_affiliation.pk)
            self.assertEqual(__prev_affiliation_dates,
                             [prev_affiliation.beginning, prev_affiliation.end+self.one_week])

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            self.assertEqual(__next_affiliation_dates, [next_affiliation.beginning, next_affiliation.end])

    def test__save__end_changes(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            __prev_affiliation_dates = [self.prev_affiliation.beginning, self.prev_affiliation.end]

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            next_affiliation.beginning = next_affiliation.beginning + self.one_week
            next_affiliation.save()
            __next_affiliation_dates = [next_affiliation.beginning, next_affiliation.end]
            mock_new_cleaning_duties.mock_calls = []

            affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
            affiliation.end = affiliation.end+self.one_week
            affiliation.save()

            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(self.end_date, self.end_date+self.one_week, 3)])

            prev_affiliation = Affiliation.objects.get(pk=self.prev_affiliation.pk)
            self.assertEqual(__prev_affiliation_dates, [prev_affiliation.beginning, prev_affiliation.end])

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            self.assertEqual(__next_affiliation_dates, [next_affiliation.beginning, next_affiliation.end])
