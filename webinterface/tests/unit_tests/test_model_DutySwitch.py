from django.test import TestCase
from webinterface.models import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithDutySwitch

import logging
from unittest.mock import *


class DutySwitchQuerySetTest(BaseFixtureWithDutySwitch, TestCase):
    def test__open__no_schedule(self):
        self.assertSetEqual(set(DutySwitch.objects.open()),
                            {self.angie_bathroom_dutyswitch_2502, self.dave_garage_dutyswitch_2500})

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

    def test__possible_acceptors(self):
        self.assertSetEqual(set(self.angie_bathroom_dutyswitch_2502.possible_acceptors()),
                            {Assignment.objects.get(schedule=self.bathroom_schedule,
                                                    cleaning_week__week=self.start_week+3)})

        self.assertSetEqual(set(self.dave_garage_dutyswitch_2500.possible_acceptors()),
                            {Assignment.objects.get(schedule=self.garage_schedule,
                                                    cleaning_week__week=self.start_week + 3)})

    def test__save__acceptor_is_set(self):
        temp_schedule = Schedule.objects.create(name='temp')
        cleaning_week_1 = CleaningWeek.objects.create(week=300, schedule=temp_schedule)
        cleaning_week_2 = CleaningWeek.objects.create(week=301, schedule=temp_schedule)

        temp_cleaner_1 = Cleaner.objects.create(name='temp1')
        temp_cleaner_2 = Cleaner.objects.create(name='temp2')

        assignment_1 = Assignment.objects.create(cleaner=temp_cleaner_1, cleaning_week=cleaning_week_1,
                                                 schedule=temp_schedule)
        assignment_2 = Assignment.objects.create(cleaner=temp_cleaner_2, cleaning_week=cleaning_week_2,
                                                 schedule=temp_schedule)

        temp_dutyswitch = DutySwitch.objects.create(requester_assignment=assignment_1)
        temp_dutyswitch.acceptor_assignment = assignment_2
        temp_dutyswitch.save()

        self.assertEqual(assignment_1.cleaner, temp_cleaner_2)
        self.assertEqual(assignment_2.cleaner, temp_cleaner_1)
        self.assertIn(temp_cleaner_1, cleaning_week_1.excluded.all())

        temp_dutyswitch.delete()
        assignment_1.delete()
        assignment_2.delete()
        temp_cleaner_1.delete()
        temp_cleaner_2.delete()
        cleaning_week_1.delete()
        cleaning_week_2.delete()
        temp_schedule.delete()

