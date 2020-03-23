from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class TaskTemplateQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.enabled_tasktemplate = TaskTemplate.objects.create(
            task_name="enabled_tasktemplate", task_disabled=False, schedule=cls.schedule,
            start_days_before=1, end_days_after=1)
        cls.disabled_tasktemplate = TaskTemplate.objects.create(
            task_name="disabled_tasktemplate", task_disabled=True, schedule=cls.schedule,
            start_days_before=1, end_days_after=1)

    def test__enabled(self):
        enabled_queryset = TaskTemplate.objects.enabled()
        self.assertIn(self.enabled_tasktemplate, enabled_queryset)
        self.assertNotIn(self.disabled_tasktemplate, enabled_queryset)

    def test__disabled(self):
        disabled_queryset = TaskTemplate.objects.disabled()
        self.assertNotIn(self.enabled_tasktemplate, disabled_queryset)
        self.assertIn(self.disabled_tasktemplate, disabled_queryset)


class TaskTemplateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.week = 2500
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.schedule2 = Schedule.objects.create(name="schedule2")
        cls.cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week,
                                                        tasks_valid=True)
        cls.cleaning_week2 = CleaningWeek.objects.create(schedule=cls.schedule2, week=cls.week + 1,
                                                         tasks_valid=True)
        cls.future_cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week + 1,
                                                               tasks_valid=True)
        cls.task_template = TaskTemplate.objects.create(schedule=cls.schedule, start_days_before=1, end_days_after=1,
                                                        task_disabled=False)

    def test__str(self):
        self.assertEqual(self.task_template.__str__(), self.task_template.task_name)

    def test__start_day_to_weekday(self):
        self.assertEqual(self.task_template.start_day_to_weekday(), Schedule.WEEKDAYS[1][1])

    def test__end_day_to_weekday(self):
        self.assertEqual(self.task_template.end_day_to_weekday(), Schedule.WEEKDAYS[3][1])

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__changing_disabled_invalidates_tasks_on_all_cleaning_weeks(self, mock_curr_epoch_week):
        mock_curr_epoch_week.return_value = self.week

        self.task_template.task_disabled = True
        self.task_template.save()

        self.assertFalse(CleaningWeek.objects.get(pk=self.future_cleaning_week.pk).tasks_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week.pk).tasks_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week2.pk).tasks_valid)
