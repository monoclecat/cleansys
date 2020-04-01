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
        cls.current_week = cls.start_week + 1

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.schedule2 = Schedule.objects.create(name="schedule2")

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        cls.group2 = ScheduleGroup.objects.create(name="group2")
        cls.group2.schedules.add(cls.schedule2)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1")
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2")

        # Affiliation
        cls.previous_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.start_week - 10, end=cls.start_week - 2)
        cls.affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.start_week, end=cls.end_week)
        cls.next_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.end_week + 2, end=cls.end_week + 10)

        [cls.schedule.cleaningweek_set.create(week=x, assignments_valid=True)
         for x in range(cls.start_week, cls.end_week)]
        [cls.schedule2.cleaningweek_set.create(week=x, assignments_valid=True)
         for x in range(cls.start_week, cls.end_week)]

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

    @patch('webinterface.models.CleaningWeek.set_assignments_valid_field', autospec=True)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__affiliation_time_frame_change_in_past_doesnt_invalidate(
            self, mock_current_epoch_week, mock_set_assignments_valid):
        mock_current_epoch_week.return_value = self.current_week

        Affiliation.cleaning_week_assignments_invalidator(
            affiliation_pk=self.affiliation.pk, prev_group=self.group, new_group=self.group,
            prev_beginning=self.start_week, prev_end=self.start_week + 3,
            new_beginning=self.start_week + 1, new_end=self.start_week + 3
        )

        self.assertListEqual(mock_set_assignments_valid.call_args_list, [])

    def assert_future_cleaning_weeks_are_invalidated(
            self, schedule: Schedule, call_args_list: list, expected_weeks: set):
        call_tuples = tuple(x[0] for x in call_args_list)
        self.assertFalse(any([x[1] for x in call_tuples]))

        cleaning_week_pks = [x[0].pk for x in call_tuples]
        cleaning_weeks = schedule.cleaningweek_set.filter(pk__in=cleaning_week_pks)

        self.assertFalse(cleaning_weeks.filter(week__lte=self.current_week).exists())
        self.assertSetEqual(set(x.week for x in cleaning_weeks.all()), expected_weeks)

    @patch('webinterface.models.CleaningWeek.set_assignments_valid_field', autospec=True)
    @patch('webinterface.models.current_epoch_week', autospec=True)
    def run_assignments_invalidator(self, mock_current_epoch_week, mock_set_assignments_valid,
                                    affiliation_pk, prev_group, new_group,
                                    prev_beginning, new_beginning, prev_end, new_end):
        mock_current_epoch_week.return_value = self.current_week
        Affiliation.cleaning_week_assignments_invalidator(
            affiliation_pk=affiliation_pk, prev_group=prev_group, new_group=new_group,
            prev_beginning=prev_beginning, prev_end=prev_end,
            new_beginning=new_beginning, new_end=new_end
        )

        return mock_set_assignments_valid.call_args_list

    def test__affiliation_time_frame_change_in_future_invalidates(self):
        call_args_list = self.run_assignments_invalidator(
            affiliation_pk=self.affiliation.pk, prev_group=self.group, new_group=self.group,
            prev_beginning=self.start_week, prev_end=self.start_week + 3,
            new_beginning=self.start_week, new_end=self.start_week + 1
        )
        self.assert_future_cleaning_weeks_are_invalidated(
            schedule=self.schedule, call_args_list=call_args_list,
            expected_weeks=set(x for x in range(self.current_week + 1, self.start_week + 4))
        )

    def test__affiliation_group_change_invalidates(self):
        call_args_list = self.run_assignments_invalidator(
            affiliation_pk=self.affiliation.pk, prev_group=self.group, new_group=self.group2,
            prev_beginning=self.start_week, prev_end=self.start_week + 3,
            new_beginning=self.start_week, new_end=self.start_week + 3
        )
        self.assert_future_cleaning_weeks_are_invalidated(
            schedule=self.schedule, call_args_list=call_args_list,
            expected_weeks=set(x for x in range(self.current_week + 1, self.start_week + 4))
        )
        self.assert_future_cleaning_weeks_are_invalidated(
            schedule=self.schedule2, call_args_list=call_args_list,
            expected_weeks=set(x for x in range(self.current_week + 1, self.start_week + 4))
        )

    def test__affiliation_creation_or_deletion_invalidates(self):
        call_args_list = self.run_assignments_invalidator(
            affiliation_pk=None, prev_group=self.group, new_group=self.group,
            prev_beginning=self.start_week, prev_end=self.start_week + 3,
            new_beginning=self.start_week, new_end=self.start_week + 3
        )
        self.assert_future_cleaning_weeks_are_invalidated(
            schedule=self.schedule, call_args_list=call_args_list,
            expected_weeks=set(x for x in range(self.current_week + 1, self.start_week + 4))
        )


class AffiliationDataBaseTests(TestCase):
    def setUp(self) -> None:
        self.start_week = 2500
        self.current_week = 2501
        self.schedule = Schedule.objects.create(name='schedule')
        self.group = ScheduleGroup.objects.create(name='group')
        self.group.schedules.add(self.schedule)
        self.schedule2 = Schedule.objects.create(name='schedule2')
        self.group2 = ScheduleGroup.objects.create(name='group2')
        self.group2.schedules.add(self.schedule2)
        self.cleaner = Cleaner.objects.create(name='cleaner')
        self.cleaner2 = Cleaner.objects.create(name='cleaner2')
        self.affiliation = Affiliation.objects.create(beginning=self.start_week, end=self.start_week+3,
                                                      cleaner=self.cleaner, group=self.group)

        [self.schedule.cleaningweek_set.create(week=x, assignments_valid=True)
         for x in range(self.start_week, self.start_week+4)]

    @patch('webinterface.models.Affiliation.cleaning_week_assignments_invalidator', autospec=True)
    def test__correct_args_to_invalidator__begin_and_end_change(self, mock_invalidator):
        self.affiliation.beginning = self.start_week + 1
        self.affiliation.end = self.start_week + 2
        self.affiliation.save()
        self.assertDictEqual(mock_invalidator.call_args[1],
                             {'affiliation_pk': self.affiliation.pk,
                              'prev_group': self.group, 'new_group': self.group,
                              'prev_beginning': self.start_week, 'prev_end': self.start_week + 3,
                              'new_beginning': self.affiliation.beginning, 'new_end': self.affiliation.end})

    @patch('webinterface.models.Affiliation.cleaning_week_assignments_invalidator', autospec=True)
    def test__correct_args_to_invalidator__group_changes(self, mock_invalidator):
        self.affiliation.group = self.group2
        self.affiliation.save()
        self.assertDictEqual(mock_invalidator.call_args[1],
                             {'affiliation_pk': self.affiliation.pk,
                              'prev_group': self.group, 'new_group': self.group2,
                              'prev_beginning': self.start_week, 'prev_end': self.start_week + 3,
                              'new_beginning': self.affiliation.beginning, 'new_end': self.affiliation.end})

    @patch('webinterface.models.Affiliation.cleaning_week_assignments_invalidator', autospec=True)
    def test__correct_args_to_invalidator__creation(self, mock_invalidator):
        Affiliation.objects.create(beginning=self.start_week, end=self.start_week+3,
                                   cleaner=self.cleaner2, group=self.group)
        self.assertDictEqual(mock_invalidator.call_args[1],
                             {'affiliation_pk': None,
                              'prev_group': self.group, 'new_group': self.group,
                              'prev_beginning': self.start_week, 'prev_end': self.start_week + 3,
                              'new_beginning': self.start_week, 'new_end': self.start_week + 3})

    @patch('webinterface.models.Affiliation.cleaning_week_assignments_invalidator', autospec=True)
    def test__correct_args_to_invalidator__deletion(self, mock_invalidator):
        self.affiliation.delete()
        self.assertDictEqual(mock_invalidator.call_args[1],
                             {'affiliation_pk': None,
                              'prev_group': self.group, 'new_group': self.group,
                              'prev_beginning': self.start_week, 'prev_end': self.start_week + 3,
                              'new_beginning': self.start_week, 'new_end': self.start_week + 3})
