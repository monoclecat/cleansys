from django.test import TestCase
from webinterface.models import *
from unittest.mock import *

from webinterface.tests.unit_tests.fixtures import BaseFixture


class ScheduleQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Schedule
        cls.enabled = Schedule.objects.create(name="enabled", disabled=False)
        cls.disabled = Schedule.objects.create(name="disabled", disabled=True)

    def test__enabled(self):
        enabled_schedules = Schedule.objects.enabled()
        self.assertIn(self.enabled, enabled_schedules)
        self.assertNotIn(self.disabled, enabled_schedules)

    def test__disabled(self):
        disabled_schedules = Schedule.objects.disabled()
        self.assertIn(self.disabled, disabled_schedules)
        self.assertNotIn(self.enabled, disabled_schedules)


class ScheduleTest(BaseFixture, TestCase):
    def test__str(self):
        schedule = Schedule(name='abc')
        self.assertEqual(schedule.__str__(), schedule.name)

    def test__deployment_ration__outside_of_active_affiliations(self):
        self.assertListEqual(self.bathroom_schedule.deployment_ratios(self.start_week - 1), [])
        self.assertListEqual(self.bathroom_schedule.deployment_ratios(self.end_week + 1), [])

    def test__deployment_ratios_are_sorted_and_correct_cleaners_are_selected(self):
        with patch.object(Cleaner, 'deployment_ratio', side_effect=[0.5, 0.3]):
            result = self.bathroom_schedule.deployment_ratios(self.start_week)
        self.assertListEqual([[self.bob, 0.3], [self.angie, 0.5]], result)

    def test__occurs_in_week(self):
        weekly_schedule = Schedule(frequency=1)
        even_week_schedule = Schedule(frequency=2)
        odd_week_schedule = Schedule(frequency=3)

        even_week = self.start_week
        odd_week = self.start_week + 1

        self.assertTrue(weekly_schedule.occurs_in_week(even_week))
        self.assertTrue(even_week_schedule.occurs_in_week(even_week))
        self.assertFalse(odd_week_schedule.occurs_in_week(even_week))

        self.assertTrue(weekly_schedule.occurs_in_week(odd_week))
        self.assertFalse(even_week_schedule.occurs_in_week(odd_week))
        self.assertTrue(odd_week_schedule.occurs_in_week(odd_week))

    @patch('webinterface.models.Schedule.create_assignment', autospec=True,
           side_effect=[x % 2 == 0 for x in range(0, 100)])
    def run_and_assert__create_assignments_over_timespan(
            self, mock_create_assignment,
            schedule: Schedule, start_week: int, end_week: int,
            expected_create_assignment_week_args: list):

        schedule.create_assignments_over_timespan(start_week, end_week)

        create_assignment_week_args = [x[1]['week'] for x in mock_create_assignment.call_args_list]

        # Note on [::2] : side_effect of mock_create_assignment causes it to be called twice
        # with the exact same arguments in while loop of create_assignments_over_timespan()
        self.assertListEqual(create_assignment_week_args[::2], expected_create_assignment_week_args)

    def test__create_assignments_over_timespan(self):
        self.run_and_assert__create_assignments_over_timespan(
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            expected_create_assignment_week_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__only_one_week(self):
        self.run_and_assert__create_assignments_over_timespan(
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.start_week,
            expected_create_assignment_week_args=[self.start_week])

    @patch('webinterface.models.CleaningWeek.excluded', autospec=True)
    @patch('webinterface.models.Schedule.deployment_ratios', autospec=True, return_value=[])
    @patch('django.db.models.query.QuerySet.create', autospec=True)
    def run_and_assert__create_assignment(
            self, mock_create, mock_deployment_ratios, mock_excluded,
            schedule: Schedule, week: int, expect_codes: set, expect_result: bool, deployment_ratios: list,
            excluded: list):

        mock_create.return_value = True
        mock_deployment_ratios.return_value = deployment_ratios
        mock_excluded.all.return_value = excluded

        with self.assertLogs(level='DEBUG') as log:
            result = schedule.create_assignment(week=week)

        all_codes = {"Code01", "Code02", "Code03", "Code04", "Code21", "Code22"}
        must_occur = expect_codes
        must_not_occur = all_codes - must_occur

        [self.assertIn(x, str(log.output)) for x in must_occur]
        [self.assertNotIn(x, str(log.output)) for x in must_not_occur]

        self.assertEqual(expect_result, result)

        if expect_result:
            self.assertRegex(str(mock_create.call_args[1]),
                             ".*'cleaning_week': <CleaningWeek.*{}.*{}.*>.*".format(schedule.name, str(week)))

    def test__create_assignment__disabled_schedule(self):
        self.run_and_assert__create_assignment(
            schedule=self.garage_schedule, week=self.start_week, expect_codes={"Code04"}, expect_result=False,
            deployment_ratios=[[self.bob, 0.9]], excluded=[])

    def test__create_assignment__even_week_schedule__not_defined_on_date(self):
        self.run_and_assert__create_assignment(
            schedule=self.kitchen_schedule, week=self.start_week+1, expect_codes={"Code01"}, expect_result=False,
            deployment_ratios=[[self.bob, 0.9]], excluded=[])

    def test__create_assignment__even_week_schedule__no_positions_to_fill(self):
        self.run_and_assert__create_assignment(
            schedule=self.bathroom_schedule, week=self.start_week, expect_codes={"Code02"}, expect_result=False,
            deployment_ratios=[[self.bob, 0.9]], excluded=[])

    def test__create_assignment__even_week_schedule__no_deployment_ratios(self):
        self.run_and_assert__create_assignment(
            schedule=self.kitchen_schedule, week=self.start_week, expect_codes={"Code03"}, expect_result=False,
            deployment_ratios=[], excluded=[])

    def test__create_assignment__even_week_schedule__every_cleaner_is_excluded(self):
        # dave is not normally assigned to this schedule. We include him to make sure the first cleaner of
        # deployment_ratios is selected as the cleaner.
        self.run_and_assert__create_assignment(
            schedule=self.kitchen_schedule, week=self.start_week, expect_codes={"Code11", "Code22"},
            expect_result=True,
            deployment_ratios=[[self.bob, 0.5], [self.dave, 0.5]], excluded=[self.bob, self.dave])


class ScheduleModelDatabaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.week = 2500
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=1, frequency=1)
        cls.schedule2 = Schedule.objects.create(name="schedule2", frequency=3)  # Only odd week numbers
        cls.cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week,
                                                        assignments_valid=True)
        cls.future_cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week+1,
                                                               assignments_valid=True)
        cls.cleaning_week_in_wrong_week = CleaningWeek.objects.create(schedule=cls.schedule2, week=cls.week+1,
                                                                      assignments_valid=True)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def invalidation_test_runner(self, mock_curr_epoch_week, field_name: str, new_value: int):
        mock_curr_epoch_week.return_value = self.week

        setattr(self.schedule, field_name, new_value)
        self.schedule.save()
        self.assertFalse(CleaningWeek.objects.get(pk=self.future_cleaning_week.pk).assignments_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week.pk).assignments_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week_in_wrong_week.pk).assignments_valid)

    def test__future_cleaning_weeks_invalidated_on_cleaners_per_date_change(self):
        self.invalidation_test_runner(field_name='cleaners_per_date', new_value=2)

    def test__future_cleaning_weeks_invalidated_on_frequency_change(self):
        self.invalidation_test_runner(field_name='frequency', new_value=2)

    def test__create_assignment_removes_misplaced_cleaning_weeks(self):
        self.schedule2.create_assignment(week=self.week)
        self.assertFalse(self.schedule2.cleaningweek_set.filter(week=self.week).exists())
