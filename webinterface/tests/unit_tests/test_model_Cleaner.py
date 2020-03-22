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
        all_schedules = [self.bathroom_schedule, self.kitchen_schedule, self.bedroom_schedule, self.garage_schedule]
        self.assertListEqual([self.angie.deployment_ratio_for_schedule(x) for x in all_schedules],
                             [0.75, 0.0, 0.0, 0.0])
        self.assertListEqual([self.bob.deployment_ratio_for_schedule(x) for x in all_schedules],
                             [0.0, 0.5, 0.5, 0.5])
        self.assertListEqual([self.chris.deployment_ratio_for_schedule(x) for x in all_schedules],
                             [0.5, 0.5, 0.5, 0.0])
        self.assertListEqual([self.dave.deployment_ratio_for_schedule(x) for x in all_schedules],
                             [0.0, 0.0, 0.0, 0.75])

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__during_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertTrue(self.angie.is_active())

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__outside_of_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week-1
        self.assertFalse(self.angie.is_active())

    @patch('webinterface.models.DutySwitch.possible_acceptors', autospec=True)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__switchable_assignments_for_request__no_active_affiliation(self,
                                                                        mock_current_epoch_week,
                                                                        mock_possible_acceptors):
        mock_current_epoch_week.return_value = self.start_week
        mock_possible_acceptors.return_value = self.garage_schedule.assignment_set.filter(cleaner=self.bob)

        # Bob can't switch with chris because bob has no active Affiliation during chris' Assignment
        assignments = self.bob.switchable_assignments_for_request(self.dave_garage_dutyswitch_2500)
        self.assertTrue(len(assignments) == 0)

        self.assertFalse(self.bob.can_accept_duty_switch_request(self.dave_garage_dutyswitch_2500))

    @patch('webinterface.models.DutySwitch.possible_acceptors', autospec=True)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__switchable_assignments_for_request__switch_possible(self,
                                                                  mock_current_epoch_week,
                                                                  mock_possible_acceptors):
        mock_current_epoch_week.return_value = self.start_week
        mock_possible_acceptors.return_value = self.bathroom_schedule.assignment_set.filter(cleaner=self.chris)

        assignments = self.chris.switchable_assignments_for_request(self.angie_bathroom_dutyswitch_2502)
        self.assertListEqual(list(assignments),
                             list(self.chris.assignment_set.filter(schedule=self.bathroom_schedule,
                                                                   cleaning_week__week=self.start_week+3)))

        self.assertTrue(self.chris.can_accept_duty_switch_request(self.angie_bathroom_dutyswitch_2502))

    def test__nr_assignments_on_day(self):
        self.assertListEqual([self.angie.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week+1)],
                             [1, 1, 1, 0])
        self.assertListEqual([self.bob.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [1, 0, 0, 2])
        self.assertListEqual([self.chris.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [0, 1, 1, 1])

    def test__is_eligible_for_date(self):
        self.assertListEqual([self.angie.is_eligible_for_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [False, False, False, True])
        self.assertListEqual([self.bob.is_eligible_for_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [True, True, True, False])
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
