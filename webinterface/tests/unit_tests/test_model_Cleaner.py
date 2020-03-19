from django.test import TestCase
from webinterface.models import *
from unittest.mock import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithDutySwitch


class CleanerTest(BaseFixtureWithDutySwitch, TestCase):
    def test__str(self):
        cleaner = Cleaner(name="bob")
        self.assertEqual(cleaner.__str__(), cleaner.name)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__current_affiliation__exists(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertEqual(self.angie.current_affiliation(), self.angie_affiliation)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__current_affiliation__does_not_exist(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week-1
        self.assertIsNone(self.angie.current_affiliation())

    def test__all_assignments_during_affiliation_with_schedule(self):
        angies_first_two_assignments = self.bob.all_assignments_during_affiliation_with_schedule(self.bathroom_schedule)

        self.assertEqual(set(angies_first_two_assignments),
                         set(self.bathroom_schedule.assignment_set.filter(
                             cleaning_week__week__gte=self.start_week,
                             cleaning_week__week__lte=self.start_week+1)))

    def test__own_assignments_during_affiliation_with_schedule(self):
        no_assignments = self.bob.own_assignments_during_affiliation_with_schedule(self.bathroom_schedule)
        self.assertEqual(list(no_assignments), [])

        one_assignment = self.bob.own_assignments_during_affiliation_with_schedule(self.kitchen_schedule)
        self.assertEqual(set(one_assignment), set(self.bob.assignment_set.filter(cleaning_week__week=self.start_week)))

    def test__deployment_ratio_for_schedule(self):
        self.assertEqual(self.bob.deployment_ratio_for_schedule(self.bathroom_schedule), 0.0)
        self.assertEqual(self.bob.deployment_ratio_for_schedule(self.kitchen_schedule), 0.5)

        self.assertEqual(self.angie.deployment_ratio_for_schedule(self.bathroom_schedule), 1.0)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__during_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertTrue(self.angie.is_active())

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__outside_of_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week-1
        self.assertFalse(self.angie.is_active())

    def test__rejected_dutyswitch_requests(self):
        self.assertEqual(list(self.angie.rejected_dutyswitch_requests()), [self.rejected_dutyswitch])
        self.assertEqual(list(self.bob.rejected_dutyswitch_requests()), [])
        self.assertEqual(list(self.chris.rejected_dutyswitch_requests()), [])
        self.assertEqual(list(self.dave.rejected_dutyswitch_requests()), [])

    def test__dutyswitch_requests_received(self):
        self.assertEqual(list(self.angie.dutyswitch_requests_received()), [self.dutyswitch_request_received])
        self.assertEqual(list(self.bob.dutyswitch_requests_received()), [])
        self.assertEqual(list(self.chris.dutyswitch_requests_received()), [])
        self.assertEqual(list(self.dave.dutyswitch_requests_received()), [])

    def test__pending_dutyswitch_requests(self):
        self.assertEqual(list(self.angie.pending_dutyswitch_requests()), [])
        self.assertEqual(list(self.bob.pending_dutyswitch_requests()), [])
        self.assertEqual(list(self.chris.pending_dutyswitch_requests()), [self.pending_dutyswitch_request])
        self.assertEqual(list(self.dave.pending_dutyswitch_requests()), [])

    def test__has_pending_requests(self):
        self.assertTrue(self.angie.has_pending_requests())
        self.assertFalse(self.bob.has_pending_requests())
        self.assertTrue(self.chris.has_pending_requests())
        self.assertFalse(self.dave.has_pending_requests())

    def test__nr_assignments_on_day(self):
        self.assertListEqual([self.angie.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week+1)],
                             [1, 1, 1, 1])
        self.assertListEqual([self.bob.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [1, 0, 0, 1])
        self.assertListEqual([self.chris.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [0, 1, 1, 0])

    def test__is_eligible_for_date(self):
        self.assertListEqual([self.angie.is_eligible_for_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [False, False, False, False])
        self.assertListEqual([self.bob.is_eligible_for_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [True, True, True, True])
        self.assertListEqual([self.chris.is_eligible_for_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [True, True, True, True])

    def test__user_is_created_with_cleaner(self):
        self.assertTrue(User.objects.filter(username=self.angie.slug).exists())
        self.assertTrue(User.objects.filter(username=self.bob.slug).exists())
        self.assertTrue(User.objects.filter(username=self.chris.slug).exists())
        self.assertTrue(User.objects.filter(username=self.dave.slug).exists())

    def test__save__name_change_triggers_slug_change(self):
        dave = Cleaner.objects.get(name='dave')
        dave.name = 'eric'
        dave.save()

        self.assertEqual(Cleaner.objects.get(name='eric').slug, 'eric')
        self.assertTrue(User.objects.filter(username=Cleaner.objects.get(name='eric').slug).exists())

        dave = Cleaner.objects.get(name='eric')
        dave.name = 'dave'
        dave.save()

        self.assertEqual(Cleaner.objects.get(name='dave').slug, 'dave')
        self.assertTrue(User.objects.filter(username=Cleaner.objects.get(name='dave').slug).exists())

    def test__save_and_delete(self):
        cleaner = Cleaner.objects.create(name='eric')

        self.assertEqual(Cleaner.objects.get(name='eric').slug, 'eric')
        self.assertTrue(User.objects.filter(username=cleaner.slug).exists())

        cleaner.delete()

        self.assertFalse(Cleaner.objects.filter(name='eric').exists())
        self.assertFalse(User.objects.filter(username='eric').exists())
