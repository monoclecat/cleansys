from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

#
# class TaskTemplateQuerySetTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.schedule = Schedule.objects.create(name="schedule")
#         cls.enabled_tasktemplate = TaskTemplate.objects.create(
#             name="enabled_tasktemplate", disabled=False, schedule=cls.schedule)
#         cls.disabled_tasktemplate = TaskTemplate.objects.create(
#             name="disabled_tasktemplate", disabled=True, schedule=cls.schedule)
#
#     def test__enabled(self):
#         enabled_queryset = TaskTemplate.objects.enabled()
#         self.assertIn(self.enabled_tasktemplate, enabled_queryset)
#         self.assertNotIn(self.disabled_tasktemplate, enabled_queryset)
#
#     def test__disabled(self):
#         disabled_queryset = TaskTemplate.objects.disabled()
#         self.assertNotIn(self.enabled_tasktemplate, disabled_queryset)
#         self.assertIn(self.disabled_tasktemplate, disabled_queryset)
#
#
# class TaskTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
#         cls.schedule = Schedule.objects.create(name="schedule")
#         cls.cleaning_day = CleaningWeek.objects.create(date=cls.reference_date, schedule=cls.schedule)
#
#     def test__creation(self):
#         task = Task.objects.create(name="task1", cleaning_day=self.cleaning_day, start_date=self.reference_date,
#                                    end_date=self.reference_date)
#         self.assertIsInstance(task, Task)
