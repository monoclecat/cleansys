from django.test import TestCase
from webinterface.models import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithTasks
from unittest.mock import *


class TaskQuerySetTest(BaseFixtureWithTasks, TestCase):
    def test__cleaned(self):
        self.assertSetEqual(set(Task.objects.cleaned()),
                            set(Task.objects.filter(cleaning_week=CleaningWeek.objects.get(
                                week=self.start_week, schedule=self.bathroom_schedule))))

    def test__uncleaned(self):
        self.assertSetEqual(set(Task.objects.uncleaned()),
                            set(Task.objects.filter(cleaning_week__schedule=self.bathroom_schedule).
                                exclude(cleaning_week=CleaningWeek.objects.get(week=self.start_week,
                                                                               schedule=self.bathroom_schedule))))


class TaskTest(BaseFixtureWithTasks, TestCase):
    def setUp(self) -> None:
        cleaning_week_2500 = self.bathroom_schedule.cleaningweek_set.get(week=self.start_week)
        self.task_bathroom_2500_1, self.task_bathroom_2500_2 = cleaning_week_2500.task_set.all()

        cleaning_week_2503 = self.bathroom_schedule.cleaningweek_set.get(week=self.end_week)
        self.task_bathroom_2503_1, self.task_bathroom_2503_2 = cleaning_week_2503.task_set.all()

    def test__str(self):
        self.assertEqual(self.task_bathroom_2500_1.__str__(), self.bathroom_task_template_1.name)

    def test__start_date(self):
        self.assertEqual(self.task_bathroom_2500_1.start_date(),
                         epoch_week_to_monday(self.start_week) + datetime.timedelta(days=1))

        self.assertEqual(self.task_bathroom_2500_2.start_date(),
                         epoch_week_to_monday(self.start_week) - datetime.timedelta(days=1))

    def test__end_date(self):
        self.assertEqual(self.task_bathroom_2500_1.end_date(),
                         epoch_week_to_monday(self.start_week) + datetime.timedelta(days=4))

        self.assertEqual(self.task_bathroom_2500_2.end_date(),
                         epoch_week_to_monday(self.start_week) + datetime.timedelta(days=5))

    @patch('django.utils.timezone.now', autospec=True)
    def test__my_time_has_come(self, mock_now):
        week = self.start_week

        mock_date = MagicMock()
        mock_date.date.return_value = epoch_week_to_monday(week)
        mock_now.return_value = mock_date

        cw = self.bathroom_schedule.cleaningweek_set.get(week=week)
        task1 = cw.task_set.get(template=self.bathroom_task_template_1)  # Can only start Tuesday
        task2 = cw.task_set.get(template=self.bathroom_task_template_2)  # Can start Sunday

        self.assertFalse(task1.my_time_has_come())
        self.assertTrue(task2.my_time_has_come())

    @patch('django.utils.timezone.now', autospec=True)
    def test__has_passed(self, mock_now):
        week = self.start_week
        cw = self.bathroom_schedule.cleaningweek_set.get(week=week)

        mock_date = MagicMock()
        mock_date.date.return_value = cw.assignment_date() + datetime.timedelta(days=3)
        mock_now.return_value = mock_date

        task1 = cw.task_set.get(template=self.bathroom_task_template_1)  # Can only be done 2 days after assignment_date
        task2 = cw.task_set.get(template=self.bathroom_task_template_2)  # Can be done 3 days after assignment_date

        self.assertTrue(task1.has_passed())
        self.assertFalse(task2.has_passed())

    def test__possible_cleaners(self):
        self.assertListEqual(list(self.task_bathroom_2500_1.possible_cleaners()), [self.angie])
        self.assertListEqual(list(self.task_bathroom_2503_1.possible_cleaners()), [self.chris])

    @patch('webinterface.models.Task.save', autospec=True)
    def test__set_assigmnents_valid_field(self, mock_save):
        week = self.start_week + 1  # In start_week, all already have cleaned_by=angie
        cw = self.bathroom_schedule.cleaningweek_set.get(week=week)
        task1 = cw.task_set.get(template=self.bathroom_task_template_1)

        self.assertEqual(task1.cleaned_by, None)
        task1.set_cleaned_by(self.angie)
        self.assertEqual(mock_save.call_args[0][0].cleaned_by, self.angie)
