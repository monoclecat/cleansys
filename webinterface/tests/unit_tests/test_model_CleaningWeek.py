from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class CleaningWeekQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.start_week = 2500
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.cw1 = CleaningWeek.objects.create(week=cls.start_week, schedule=cls.schedule,
                                              disabled=False, assignments_valid=True)
        cls.cw2 = CleaningWeek.objects.create(week=cls.start_week + 1, schedule=cls.schedule,
                                              disabled=True, assignments_valid=True)
        cls.cw3 = CleaningWeek.objects.create(week=cls.start_week + 2, schedule=cls.schedule,
                                              disabled=False, assignments_valid=True)
        cls.cw4 = CleaningWeek.objects.create(week=cls.start_week + 3, schedule=cls.schedule,
                                              disabled=False, assignments_valid=False)

    def test__enabled(self):
        enabled_schedules = CleaningWeek.objects.enabled()
        self.assertSetEqual(set(enabled_schedules), {self.cw1, self.cw3, self.cw4})

    def test__disabled(self):
        disabled_schedules = CleaningWeek.objects.disabled()
        self.assertSetEqual(set(disabled_schedules), {self.cw2})

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__in_future(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week + 1
        future_cleaning_weeks = CleaningWeek.objects.in_future()
        self.assertSetEqual(set(future_cleaning_weeks), {self.cw3, self.cw4})

    def test__assignments_valid(self):
        assignments_valid = CleaningWeek.objects.assignments_valid()
        self.assertSetEqual(set(assignments_valid), {self.cw1, self.cw2, self.cw3})

    def test__assignments_invalid(self):
        assignments_invalid = CleaningWeek.objects.assignments_invalid()
        self.assertSetEqual(set(assignments_invalid), {self.cw4})


class CleaningWeekTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.start_week = 2500
        cls.schedule = Schedule.objects.create(name="schedule", weekday=5)
        cls.cw1 = CleaningWeek.objects.create(week=cls.start_week, schedule=cls.schedule, assignments_valid=True)
        cls.cw2 = CleaningWeek.objects.create(week=cls.start_week + 1, schedule=cls.schedule, assignments_valid=True)
        cls.cleaner = Cleaner.objects.create(name="cleaner")
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2")

        cls.assignment = Assignment.objects.create(cleaner=cls.cleaner, cleaning_week=cls.cw1, schedule=cls.schedule)

        cls.task_template_1 = TaskTemplate.objects.create(
            name="tasktemplate1", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.task_template_2 = TaskTemplate.objects.create(
            name="tasktemplate2", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.task_template_3 = TaskTemplate.objects.create(
            name="tasktemplate3", schedule=cls.schedule, start_days_before=1, end_days_after=2)

        cls.task1_cw1 = Task.objects.create(cleaning_week=cls.cw1, template=cls.task_template_1,
                                            cleaned_by=None)
        cls.task2_cw1 = Task.objects.create(cleaning_week=cls.cw1, template=cls.task_template_2,
                                            cleaned_by=cls.cleaner)

        cls.task1_cw2 = Task.objects.create(cleaning_week=cls.cw2, template=cls.task_template_1,
                                            cleaned_by=cls.cleaner)

    def test__str(self):
        string_repr = self.cw1.__str__()
        self.assertIn(self.schedule.name, string_repr)
        self.assertIn(str(self.cw1.week), string_repr)

    def test__assignment_date(self):
        self.assertEqual(self.cw1.assignment_date(),
                         epoch_week_to_monday(self.start_week) + datetime.timedelta(days=5))

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_current_week__true(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertTrue(self.cw1.is_current_week())

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_current_week__false(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week + 1
        self.assertFalse(self.cw1.is_current_week())

    @patch('webinterface.models.Task.my_time_has_come', autospec=True)
    def test__tasks_are_ready_to_be_done__are_ready(self, mock_time_has_come):
        mock_time_has_come.return_value = True
        self.assertTrue(self.cw1.tasks_are_ready_to_be_done())

    @patch('webinterface.models.Task.my_time_has_come', autospec=True)
    def test__tasks_are_ready_to_be_done__are_not_ready(self, mock_time_has_come):
        mock_time_has_come.return_value = False
        self.assertFalse(self.cw1.tasks_are_ready_to_be_done())

    def test__task_templates_missing(self):
        self.assertListEqual(list(self.cw1.task_templates_missing()),
                             [self.task_template_3])

    @patch('django.db.models.query.QuerySet.create', autospec=True)
    @patch('webinterface.models.CleaningWeek.save', autospec=True)
    def test__create_missing_tasks(self, mock_cleaning_week_save, mock_queryset_create):
        self.cw1.create_missing_tasks()

        self.assertEqual(mock_queryset_create.call_count, 1)
        self.assertEqual(mock_queryset_create.call_args[1]['template'], self.task_template_3)

    def test__completed_tasks(self):
        self.assertSetEqual(set(self.cw1.completed_tasks()), {self.task2_cw1})

    def test__completed_tasks__as_templates(self):
        self.assertSetEqual(set(self.cw1.completed_tasks__as_templates()), {self.task_template_2})

    def test__open_tasks(self):
        self.assertSetEqual(set(self.cw1.open_tasks()), {self.task1_cw1})

    def test__open_tasks__as_templates(self):
        self.assertSetEqual(set(self.cw1.open_tasks__as_templates()), {self.task_template_1})

    def test__ratio_of_completed_tasks__one_of_two(self):
        self.assertEqual(self.cw1.ratio_of_completed_tasks(), 0.5)

    def test__ratio_of_completed_tasks__all_are_done(self):
        self.assertEqual(self.cw2.ratio_of_completed_tasks(), 1.0)

    def test__all_tasks_are_completed__false(self):
        self.assertFalse(self.cw1.all_tasks_are_completed())

    def test__all_tasks_are_completed__true(self):
        self.assertTrue(self.cw2.all_tasks_are_completed())

    def test__assigned_cleaners(self):
        self.assertSetEqual(set(self.cw1.assigned_cleaners().all()), {self.cleaner})

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_in_future(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertFalse(self.cw1.is_in_future())
        self.assertTrue(self.cw2.is_in_future())

    def test__week_start(self):
        self.assertEqual(self.cw1.week_start(), epoch_week_to_monday(self.start_week))

    def test__week_end(self):
        self.assertEqual(self.cw1.week_end(), epoch_week_to_sunday(self.start_week))

    @patch('webinterface.models.CleaningWeek.save', autospec=True)
    def test__set_assigmnents_valid_field(self, mock_save):
        self.cw1.set_assignments_valid_field(False)
        self.assertFalse(mock_save.call_args[0][0].assignments_valid)
