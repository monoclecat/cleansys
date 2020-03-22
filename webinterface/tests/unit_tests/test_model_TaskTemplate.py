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
        cls.reference_week = 2500
        cls.schedule = Schedule.objects.create(name="schedule", weekday=2)
        cls.task_template = TaskTemplate.objects.create(schedule=cls.schedule, start_days_before=1, end_days_after=1)

    def test__str(self):
        self.assertEqual(self.task_template.__str__(), self.task_template.task_name)

    def test__start_day_to_weekday(self):
        self.assertEqual(self.task_template.start_day_to_weekday(), Schedule.WEEKDAYS[1][1])

    def test__end_day_to_weekday(self):
        self.assertEqual(self.task_template.end_day_to_weekday(), Schedule.WEEKDAYS[3][1])
