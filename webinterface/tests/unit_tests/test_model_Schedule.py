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
        with patch.object(Cleaner, 'deployment_ratio_for_schedule', side_effect=[0.5, 0.3]):
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
    @patch('django.db.models.query.QuerySet.delete', autospec=True)
    def run_and_assert__create_assignments_over_timespan(
            self, mock_queryset_delete, mock_create_assignment,
            schedule: Schedule, start_week: int, end_week: int,
            mode: int, assignments_should_be_deleted: bool, cleaningweeks_should_be_deleted: bool,
            expected_create_assignment_week_args: list):

        # Mocking create_assignment_directly means we are ignoring the cleaners_per_date property of Schedule
        schedule.create_assignments_over_timespan(start_week, end_week, mode)

        cleaningweek_delete_called = str(mock_queryset_delete.call_args_list).find('CleaningWeek') != -1
        assignment_delete_called = str(mock_queryset_delete.call_args_list).find('Assignment') != -1

        self.assertEqual(assignments_should_be_deleted, assignment_delete_called, msg="mode={}".format(mode))
        self.assertEqual(cleaningweeks_should_be_deleted, cleaningweek_delete_called, msg="mode={}".format(mode))

        create_assignment_week_args = [x[1]['week'] for x in mock_create_assignment.call_args_list]

        # Note on [::2] : side_effect of mock_create_assignment causes it to be called twice
        # with the exact same arguments in while loop of create_assignments_over_timespan()
        self.assertListEqual(create_assignment_week_args[::2], expected_create_assignment_week_args,
                             msg="mode={}".format(mode))

    def test__create_assignments_over_timespan__mode_1(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=1,  # Delete existing Assignments and CleaningDays and regenerate them throughout time frame
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=True, cleaningweeks_should_be_deleted=True,
            expected_create_assignment_week_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__mode_2(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=2,  # Keep existing Assignments and only create new ones where there are none already
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=False, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_week_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__mode_3(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=3,  # Only reassign Assignments on existing CleaningDays, don't generate new CleaningDays
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=True, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_week_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__only_one_week(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=2,
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.start_week,
            assignments_should_be_deleted=False, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_week_args=[self.start_week])

    def test__create_assignments_over_timespan__invalid_mode(self):
        self.assertRaisesRegex(ValueError, 'create_assignments_over_timespan.*1.*2.*3.*',
                               self.bathroom_schedule.create_assignments_over_timespan,
                               mode=4, start_week=self.start_week, end_week=self.end_week)

    def test__create_assignments__even_week_schedule__not_defined_on_date(self):
        with self.assertLogs(level='DEBUG') as log:
            result = self.kitchen_schedule.create_assignment(self.start_week+1)

        self.assertTrue(str(log.output).find('[Code01]'))
        self.assertFalse(result)

    def test__create_assignments__even_week_schedule__no_positions_to_fill(self):
        with self.assertLogs(level='DEBUG') as log:
            result = self.bathroom_schedule.create_assignment(self.start_week)

        self.assertTrue(str(log.output).find('[Code02]'))
        self.assertFalse(result)

    @patch('webinterface.models.Schedule.deployment_ratios', autospec=True, return_value=[])
    def test__create_assignments__even_week_schedule__no_deployment_ratios(self, mock_deployment_ratios):
        with self.assertLogs(level='DEBUG') as log:
            result = self.kitchen_schedule.create_assignment(self.start_week)

        self.assertTrue(str(log.output).find('[Code03]'))
        self.assertFalse(result)

    @patch('django.db.models.query.QuerySet.create', autospec=True)
    @patch('webinterface.models.CleaningWeek.excluded', autospec=True)
    @patch('webinterface.models.Schedule.deployment_ratios', autospec=True)
    def test__create_assignments__even_week_schedule__every_cleaner_is_excluded(self,
                                                                                mock_deployment_ratios,
                                                                                mock_cleaningweek_excluded,
                                                                                mock_queryset_create):
        mock_queryset_create.return_value = "return value of create"

        # dave is not normally assigned to this schedule. We include him to make sure the first cleaner of
        # deployment_ratios is selected as the cleaner.
        mock_deployment_ratios.return_value = [[self.bob, 0.5], [self.dave, 0.6]]

        mock_cleaningweek_excluded.all.return_value = [self.bob, self.dave]
        with self.assertLogs(level='DEBUG') as log:
            result = self.kitchen_schedule.create_assignment(self.start_week)

        self.assertEqual(result, "return value of create")
        self.assertTrue(str(log.output).find('[Code11]'))
        self.assertTrue(str(log.output).find('[Code22]'))
        self.assertTrue(str(mock_queryset_create.call_args[1]).find("'cleaner': <Cleaner: bob>") != -1)
        self.assertTrue(str(mock_queryset_create.call_args[1]).find(
            "'cleaning_week': <CleaningWeek: kitchen: Week 2500>") != -1)

    @patch('django.db.models.query.QuerySet.create', autospec=True)
    @patch('webinterface.models.CleaningWeek.excluded', autospec=True)
    @patch('webinterface.models.Schedule.deployment_ratios', autospec=True)
    @patch('webinterface.models.Cleaner.is_eligible_for_week', autospec=True, side_effect=[False, True])
    def test__create_assignments__even_week_schedule__second_cleaner_is_chosen(self,
                                                                               mock_cleaner_is_eligible,
                                                                               mock_deployment_ratios,
                                                                               mock_cleaningweek_excluded,
                                                                               mock_queryset_create):
        mock_queryset_create.return_value = "return value of create"

        # dave is not normally assigned to this schedule. We include him to make sure the first cleaner of
        # deployment_ratios is selected as the cleaner.
        mock_deployment_ratios.return_value = [[self.bob, 0.5], [self.dave, 0.6]]

        mock_cleaningweek_excluded.all.return_value = []
        with self.assertLogs(level='DEBUG') as log:
            result = self.kitchen_schedule.create_assignment(self.start_week)

        self.assertEqual(result, "return value of create")
        self.assertEqual(mock_cleaner_is_eligible.call_count, 2)
        self.assertTrue(str(log.output).find('[Code12]'))
        self.assertTrue(str(log.output).find('[Code21]'))
        self.assertTrue(str(mock_queryset_create.call_args[1]).find("'cleaner': <Cleaner: dave>") != -1)
        self.assertTrue(str(mock_queryset_create.call_args[1]).find(
            "'cleaning_week': <CleaningWeek: kitchen: Week 2500>") != -1)


class ScheduleDatabaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.week = 2500
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=1, frequency=1)
        cls.schedule2 = Schedule.objects.create(name="schedule2")
        cls.cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week,
                                                        assignments_valid=True)
        cls.future_cleaning_week = CleaningWeek.objects.create(schedule=cls.schedule, week=cls.week+1,
                                                               assignments_valid=True)
        cls.cleaning_week2 = CleaningWeek.objects.create(schedule=cls.schedule2, week=cls.week+1,
                                                         assignments_valid=True)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def invalidation_test_runner(self, mock_curr_epoch_week, field_name: str, new_value: int):
        mock_curr_epoch_week.return_value = self.week

        setattr(self.schedule, field_name, new_value)
        self.schedule.save()
        self.assertFalse(CleaningWeek.objects.get(pk=self.future_cleaning_week.pk).assignments_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week.pk).assignments_valid)
        self.assertTrue(CleaningWeek.objects.get(pk=self.cleaning_week2.pk).assignments_valid)

    def test_future_cleaning_weeks_invalidated_on_cleaners_per_date_change(self):
        self.invalidation_test_runner(field_name='cleaners_per_date', new_value=2)

    def test_future_cleaning_weeks_invalidated_on_frequency_change(self):
        self.invalidation_test_runner(field_name='frequency', new_value=2)
