from django.test import TestCase
from webinterface.models import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithTasks


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
        self.assertEqual(self.task_bathroom_2500_1.__str__(), self.bathroom_task_template_1.task_name)

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

    def test__possible_cleaners(self):
        self.assertListEqual(list(self.task_bathroom_2500_1.possible_cleaners()), [self.angie])
        self.assertListEqual(list(self.task_bathroom_2503_1.possible_cleaners()), [self.chris])
