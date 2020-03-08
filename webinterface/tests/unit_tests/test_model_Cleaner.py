from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class CleanerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_datetime = datetime.datetime(2010, 1, 8)
        cls.reference_date = correct_dates_to_due_day(cls.reference_datetime.date())
        cls.one_week = timezone.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=2)
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_day1 = CleaningWeek.objects.create(
            date=correct_dates_to_due_day(cls.reference_date), schedule=cls.schedule)
        cls.cleaning_day2 = CleaningWeek.objects.create(date=correct_dates_to_due_day(
            cls.reference_date + cls.one_week), schedule=cls.schedule)
        cls.cleaning_day3 = CleaningWeek.objects.create(date=correct_dates_to_due_day(
            cls.reference_date - cls.one_week), schedule=cls.schedule)

        # Affiliations
        cls.cleaner1_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.reference_date, end=cls.reference_date+2*cls.one_week)
        cls.cleaner2_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner2, group=cls.group, beginning=cls.reference_date, end=cls.reference_date+2*cls.one_week)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment4 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment_outside_of_affiliation = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day3)

        # DutySwitch Requests
        cls.rejected_dutyswitch = DutySwitch.objects.create(status=2, source_assignment=cls.assignment1)
        cls.dutyswitch_request_received = DutySwitch.objects.create(source_assignment=cls.assignment2,
                                                                    selected_assignment=cls.assignment1)
        cls.pending_dutyswitch_request = DutySwitch.objects.create(status=1, source_assignment=cls.assignment1)

    def test__creation(self):
        cleaner = Cleaner.objects.create(name="bob")
        self.assertIsInstance(cleaner, Cleaner)
        self.assertEqual(cleaner.slug, slugify(cleaner.name))

    def test__str(self):
        cleaner = Cleaner(name="bob")
        self.assertEqual(cleaner.__str__(), cleaner.name)

    def test__current_affiliation__exists(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime + self.one_week) as mock_now:
            self.assertEqual(self.cleaner1.current_affiliation(), self.cleaner1_affiliation)

    def test__current_affiliation__none(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime - self.one_week) as mock_now:
            self.assertIsNone(self.cleaner1.current_affiliation())

    def test__all_assignments_during_affiliation_with_schedule(self):
        all_assignments = self.cleaner1.all_assignments_during_affiliation_with_schedule(self.schedule)

        self.assertIn(self.assignment1, all_assignments)
        self.assertIn(self.assignment2, all_assignments)
        self.assertIn(self.assignment3, all_assignments)
        self.assertIn(self.assignment4, all_assignments)
        self.assertNotIn(self.assignment_outside_of_affiliation, all_assignments)

    def test__own_assignments_during_affiliation_with_schedule(self):
        assignments_cleaner1 = self.cleaner1.own_assignments_during_affiliation_with_schedule(self.schedule)
        assignments_cleaner2 = self.cleaner2.own_assignments_during_affiliation_with_schedule(self.schedule)

        self.assertIn(self.assignment1, assignments_cleaner1)
        self.assertNotIn(self.assignment2, assignments_cleaner1)
        self.assertNotIn(self.assignment3, assignments_cleaner1)
        self.assertNotIn(self.assignment4, assignments_cleaner1)
        self.assertNotIn(self.assignment_outside_of_affiliation, assignments_cleaner1)

        self.assertNotIn(self.assignment1, assignments_cleaner2)
        self.assertIn(self.assignment2, assignments_cleaner2)
        self.assertIn(self.assignment3, assignments_cleaner2)
        self.assertIn(self.assignment4, assignments_cleaner2)
        self.assertNotIn(self.assignment_outside_of_affiliation, assignments_cleaner2)

    def test__deployment_ratio_for_schedule(self):
        cleaner1_ratio = self.cleaner1.deployment_ratio_for_schedule(self.schedule)
        cleaner2_ratio = self.cleaner2.deployment_ratio_for_schedule(self.schedule)

        self.assertEqual(cleaner1_ratio, 1/4)
        self.assertEqual(cleaner2_ratio, 3/4)

    def test__is_active(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime + self.one_week) as mock_now:
            self.assertTrue(self.cleaner1.is_active())
        with patch.object(timezone, 'now', return_value=self.reference_datetime - self.one_week) as mock_now:
            self.assertFalse(self.cleaner1.is_active())

    def test__rejected_dutyswitch_requests(self):
        rejected_dutyswitch_requests = self.cleaner1.rejected_dutyswitch_requests()
        self.assertIn(self.rejected_dutyswitch, rejected_dutyswitch_requests)
        self.assertNotIn(self.dutyswitch_request_received, rejected_dutyswitch_requests)
        self.assertNotIn(self.pending_dutyswitch_request, rejected_dutyswitch_requests)

    def test__dutyswitch_requests_received(self):
        dutyswitch_requests_received = self.cleaner1.dutyswitch_requests_received()
        self.assertNotIn(self.rejected_dutyswitch, dutyswitch_requests_received)
        self.assertIn(self.dutyswitch_request_received, dutyswitch_requests_received)
        self.assertNotIn(self.pending_dutyswitch_request, dutyswitch_requests_received)

    def test__pending_dutyswitch_requests(self):
        pending_dutyswitch_requests = self.cleaner1.pending_dutyswitch_requests()
        self.assertNotIn(self.rejected_dutyswitch, pending_dutyswitch_requests)
        self.assertNotIn(self.dutyswitch_request_received, pending_dutyswitch_requests)
        self.assertIn(self.pending_dutyswitch_request, pending_dutyswitch_requests)

    def test__has_pending_requests(self):
        self.assertTrue(self.cleaner1.has_pending_requests())
        self.assertFalse(self.cleaner3.has_pending_requests())

    def test__nr_assignments_on_day(self):
        self.assertEqual(self.cleaner1.nr_assignments_on_day(self.cleaning_day1.date), 1)
        self.assertEqual(self.cleaner1.nr_assignments_on_day(self.cleaning_day2.date), 0)

    def test__is_eligible_for_date(self):
        self.assertFalse(self.cleaner1.is_eligible_for_date(self.cleaning_day1.date))
        self.assertTrue(self.cleaner1.is_eligible_for_date(self.cleaning_day2.date))

        self.assertTrue(self.cleaner2.is_eligible_for_date(self.cleaning_day1.date))
        self.assertFalse(self.cleaner2.is_eligible_for_date(self.cleaning_day2.date))

    def test__delete(self):
        cleaner_to_delete = Cleaner.objects.create(name="cleaner_to_delete")
        user_to_delete = cleaner_to_delete.user
        cleaner_to_delete.delete()
        self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())

    def test__save__slug_changes(self):
        cleaner = Cleaner.objects.create(name="cleaner_original_slug")
        cleaner.name = "cleaner_new_slug"
        with patch.object(User, "set_password") as mock_user_set_pw:
            cleaner.save()
            self.assertEqual(cleaner.user.username, cleaner.slug)
            self.assertListEqual(mock_user_set_pw.mock_calls, [call(cleaner.slug)])

    def test__save__new_slug(self):
        cleaner = Cleaner.objects.create(name="new_cleaner")
        self.assertTrue(User.objects.filter(username=cleaner.slug).exists())
        user = User.objects.get(username=cleaner.slug)
        self.assertTrue(User.objects.filter(username=cleaner.slug).first().check_password(cleaner.slug))
