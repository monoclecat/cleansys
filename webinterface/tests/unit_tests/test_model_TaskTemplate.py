from django.test import TestCase
from webinterface.models import *

from unittest.mock import *


class TaskTemplateTest(TestCase):
    def setUp(self):
        self.start_week = 2500
        self.schedule = Schedule.objects.create(name="schedule", weekday=3)
        self.cw1 = CleaningWeek.objects.create(schedule=self.schedule, week=self.start_week)
        self.cw2 = CleaningWeek.objects.create(schedule=self.schedule, week=self.start_week+1)
        self.cw3 = CleaningWeek.objects.create(schedule=self.schedule, week=self.start_week+2)

        self.task_template = TaskTemplate.objects.create(
            task_name='task1', schedule=self.schedule, start_days_before=1, end_days_after=1)

        self.task_cw1 = Task.objects.create(cleaning_week=self.cw1, template=self.task_template)
        self.task_cw2 = Task.objects.create(cleaning_week=self.cw2, template=self.task_template)
        self.task_cw3 = Task.objects.create(cleaning_week=self.cw3, template=self.task_template)

    def test__str(self):
        self.assertEqual(self.task_template.__str__(), self.task_template.task_name)

    def test__start_day_to_weekday(self):
        self.assertEqual(self.task_template.start_day_to_weekday(), Schedule.WEEKDAYS[2][1])

    def test__end_day_to_weekday(self):
        self.assertEqual(self.task_template.end_day_to_weekday(), Schedule.WEEKDAYS[4][1])

    @patch('webinterface.models.current_epoch_week', autospec=True)
    @patch('webinterface.models.CleaningWeek.create_missing_tasks', autospec=True)
    def test__creation_triggers_task_creation(self, mock_create_missing, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        TaskTemplate.objects.create(task_name='task2', schedule=self.schedule, start_days_before=1, end_days_after=1)
        self.assertSetEqual(set(x[0][0] for x in mock_create_missing.call_args_list),
                            {self.cw2, self.cw3})

    def test__deletion_cascades_to_tasks(self):
        self.task_template.delete()
        self.assertFalse(Task.objects.exists())
