from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class CleaningWeekQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_week1 = 2500
        cls.reference_week2 = 2501
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.enabled = CleaningWeek.objects.create(week=cls.reference_week1, schedule=cls.schedule, disabled=False)
        cls.disabled = CleaningWeek.objects.create(week=cls.reference_week2, schedule=cls.schedule, disabled=True)

    def test__enabled(self):
        enabled_schedules = CleaningWeek.objects.enabled()
        self.assertIn(self.enabled, enabled_schedules)
        self.assertNotIn(self.disabled, enabled_schedules)

    def test__disabled(self):
        disabled_schedules = CleaningWeek.objects.disabled()
        self.assertIn(self.disabled, disabled_schedules)
        self.assertNotIn(self.enabled, disabled_schedules)


class CleaningWeekTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_week = 2500
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.cleaning_week = CleaningWeek.objects.create(week=cls.reference_week, schedule=cls.schedule)

        cls.task_template_1 = TaskTemplate.objects.create(
            task_name="tasktemplate1", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.task_template_2 = TaskTemplate.objects.create(
            task_name="tasktemplate2", schedule=cls.schedule, start_days_before=1, end_days_after=2)
        cls.task_template_3 = TaskTemplate.objects.create(
            task_name="tasktemplate3", schedule=cls.schedule, start_days_before=1, end_days_after=2, task_disabled=True)

        cls.task_1 = Task.objects.create(cleaning_week=cls.cleaning_week, template=cls.task_template_1)

    def test__str(self):
        string_repr = self.cleaning_week.__str__()
        self.assertIn(self.schedule.name, string_repr)
        self.assertIn(str(self.cleaning_week.week), string_repr)

    def test__task_templates_missing(self):
        self.assertListEqual(list(self.cleaning_week.task_templates_missing()),
                             [self.task_template_2])

    @patch('django.db.models.query.QuerySet.create', autospec=True)
    @patch('webinterface.models.CleaningWeek.save', autospec=True)
    def test__create_missing_tasks(self, mock_cleaning_week_save, mock_queryset_create):
        self.cleaning_week.create_missing_tasks()

        self.assertEqual(mock_queryset_create.call_count, 1)
        self.assertEqual(mock_queryset_create.call_args[1]['template'], self.task_template_2)

    def test__week_start(self):
        self.assertEqual(self.cleaning_week.week_start(), epoch_week_to_monday(self.reference_week))

    def test__week_end(self):
        self.assertEqual(self.cleaning_week.week_end(), epoch_week_to_sunday(self.reference_week))