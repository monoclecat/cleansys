from django.test import TestCase
from webinterface.models import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithDutySwitch

import logging
from unittest.mock import *


class DutySwitchQuerySetTest(BaseFixtureWithDutySwitch, TestCase):
    def test__open__no_schedule(self):
        self.assertSetEqual(set(DutySwitch.objects.open()),
                            {self.angie_bathroom_dutyswitch_2502, self.dave_garage_dutyswitch_2500,
                             self.bob_bedroom_dutyswitch_2503, self.bob_garage_dutyswitch_2503})

    def test__open__with_schedule(self):
        self.assertSetEqual(set(DutySwitch.objects.open(self.bathroom_schedule)), {self.angie_bathroom_dutyswitch_2502})

    def test__closed__no_schedule(self):
        self.assertSetEqual(set(DutySwitch.objects.closed()), {self.completed_garage_dutyswitch})

    def test__closed__with_schedule(self):
        self.assertTrue(len(DutySwitch.objects.closed(self.bathroom_schedule)) == 0)
        self.assertSetEqual(set(DutySwitch.objects.closed(self.garage_schedule)), {self.completed_garage_dutyswitch})


class DutySwitchTest(BaseFixtureWithDutySwitch, TestCase):
    def test__str__with_acceptor(self):
        string = self.completed_garage_dutyswitch.__str__()
        self.assertIn(self.dave.name, string)
        self.assertIn(self.bob.name, string)

    def test__str__no_acceptor(self):
        string = self.angie_bathroom_dutyswitch_2502.__str__()
        self.assertIn(self.angie.name, string)

    @patch('webinterface.models.Assignment.has_passed', autospec=True, return_value=False)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__possible_acceptors(self, mock_current_epoch_week, mock_has_passed):
        mock_current_epoch_week.return_value = self.start_week

        self.assertSetEqual(set(self.angie_bathroom_dutyswitch_2502.possible_acceptors()),
                            set(Assignment.objects.filter(
                                schedule=self.bathroom_schedule,
                                cleaning_week__week=self.start_week+3))
                            )

        self.assertSetEqual(set(self.dave_garage_dutyswitch_2500.possible_acceptors()),
                            set(Assignment.objects.filter(
                                schedule=self.garage_schedule,
                                cleaning_week__week=self.start_week + 3))
                            )

        self.assertSetEqual(set(self.bob_bedroom_dutyswitch_2503.possible_acceptors()),
                            set(Assignment.objects.filter(
                                schedule=self.bedroom_schedule,
                                cleaning_week__week=self.start_week + 1))
                            )

        self.assertSetEqual(set(self.bob_garage_dutyswitch_2503.possible_acceptors()),
                            set(Assignment.objects.filter(
                                schedule=self.garage_schedule,
                                cleaning_week__week__range=(self.start_week, self.start_week + 2)))
                            )

    @patch('webinterface.models.Assignment.has_passed', autospec=True, return_value=True)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__requester_assignment_has_passed(self, mock_current_epoch_week, mock_has_passed):
        mock_current_epoch_week.return_value = self.start_week
        self.assertFalse(self.angie_bathroom_dutyswitch_2502.possible_acceptors().exists())
        self.assertFalse(self.dave_garage_dutyswitch_2500.possible_acceptors().exists())

    @patch('webinterface.models.Assignment.has_passed', autospec=True, side_effect=[False, True, False, False, False])
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__one_acceptor_has_passed(self, mock_current_epoch_week, mock_has_passed):
        mock_current_epoch_week.return_value = self.start_week

        # has_passed will return True on its second call, on dave's garage duty in start_week
        self.assertSetEqual(set(self.bob_garage_dutyswitch_2503.possible_acceptors()),
                            set(Assignment.objects.filter(
                                schedule=self.garage_schedule,
                                cleaning_week__week__range=(self.start_week+1, self.start_week + 2)))
                            )


class DutySwitchDatabaseTests(TestCase):
    def setUp(self) -> None:
        self.schedule = Schedule.objects.create(name='schedule')
        self.cleaning_week_1 = CleaningWeek.objects.create(week=300, schedule=self.schedule)
        self.cleaning_week_2 = CleaningWeek.objects.create(week=301, schedule=self.schedule)

        self.cleaner1 = Cleaner.objects.create(name='cleaner1')
        self.cleaner2 = Cleaner.objects.create(name='cleaner2')

        self.assignment1 = Assignment.objects.create(cleaner=self.cleaner1, cleaning_week=self.cleaning_week_1,
                                                     schedule=self.schedule)
        self.assignment2 = Assignment.objects.create(cleaner=self.cleaner2, cleaning_week=self.cleaning_week_2,
                                                     schedule=self.schedule)

    def test__save__acceptor_is_set(self):

        temp_dutyswitch = DutySwitch.objects.create(requester_assignment=self.assignment1)
        temp_dutyswitch.acceptor_assignment = self.assignment2
        temp_dutyswitch.save()

        self.assertEqual(self.assignment1.cleaner, self.cleaner2)
        self.assertEqual(self.assignment2.cleaner, self.cleaner1)
        self.assertIn(self.cleaner1, self.cleaning_week_1.excluded.all())
