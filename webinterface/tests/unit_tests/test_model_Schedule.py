from django.test import TestCase
from webinterface.models import *

from unittest.mock import *


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


class CompleteTestEnvironment:
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.start_week = 2500
        cls.mid_week = cls.start_week + 1
        cls.end_week = cls.start_week + 3  # 4 weeks total

        # Schedule
        cls.bathroom_schedule = Schedule.objects.create(name="bathroom", cleaners_per_date=1, weekday=2,
                                                        frequency=1)
        cls.kitchen_schedule = Schedule.objects.create(name="kitchen", cleaners_per_date=2, weekday=4,
                                                       frequency=2)
        cls.bedroom_schedule = Schedule.objects.create(name="bedroom", cleaners_per_date=2, weekday=6,
                                                       frequency=3)
        cls.garage_schedule = Schedule.objects.create(name="garage", cleaners_per_date=1, weekday=0,
                                                      frequency=1, disabled=True)

        # ScheduleGroup
        cls.upper_group = ScheduleGroup.objects.create(name="upper")
        cls.upper_group.schedules.add(cls.bathroom_schedule, cls.kitchen_schedule, cls.bedroom_schedule)

        cls.lower_group = ScheduleGroup.objects.create(name="lower")
        cls.lower_group.schedules.add(cls.kitchen_schedule, cls.bedroom_schedule, cls.garage_schedule)

        # Cleaners
        cls.angie = Cleaner.objects.create(name="angie", preference=1)  # Max one duty a week please
        cls.angie_affiliation = Affiliation.objects.create(
            cleaner=cls.angie, group=cls.upper_group, beginning=cls.start_week, end=cls.end_week
        )

        cls.bob = Cleaner.objects.create(name="bob", preference=2)  # Max two duties a week please
        cls.bob_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.upper_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.bob_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.lower_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.chris = Cleaner.objects.create(name="chris", preference=3)  # I don't care how many duties a week
        cls.chris_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.lower_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.chris_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.upper_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.dave = Cleaner.objects.create(name="dave", preference=3)  # I don't care how many duties a week
        cls.dave_affiliation = Affiliation.objects.create(
            cleaner=cls.dave, group=cls.lower_group, beginning=cls.start_week, end=cls.end_week
        )

        # CleaningWeeks
        configuration = {
            2500: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: cls.bob,
                cls.bedroom_schedule: None,  # Bedroom is only defined on odd week numbers
                cls.garage_schedule: cls.dave
            },
            2501: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: None,  # Kitchen is only defined on even week numbers
                cls.bedroom_schedule: cls.chris,
                cls.garage_schedule: cls.dave
            },
            2502: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: cls.chris,
                cls.bedroom_schedule: None,  # Bedroom is only defined on odd week numbers
                cls.garage_schedule: cls.dave
            },
            2503: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: None,  # Kitchen is only defined on even week numbers
                cls.bedroom_schedule: cls.bob,
                cls.garage_schedule: cls.dave
            },
        }

        for week, schedule_and_cleaner in configuration.items():
            for schedule, cleaner in schedule_and_cleaner.items():
                if cleaner is not None:
                    cleaning_week = CleaningWeek.objects.create(week=week, schedule=schedule)
                    setattr(cls, "{}_cleaning_week_{}".format(schedule.name, week),
                            cleaning_week
                            )
                    setattr(cls, "{}_for_{}_in_week_{}".format(cleaner, schedule.name, week),
                            Assignment.objects.create(cleaner=cleaner, schedule=schedule, cleaning_week=cleaning_week)
                            )

        print('hi')
        #
        # # DutySwitch Requests
        # cls.rejected_dutyswitch = DutySwitch.objects.create(status=2, source_assignment=cls.assignment1)
        # cls.dutyswitch_request_received = DutySwitch.objects.create(source_assignment=cls.assignment2,
        #                                                             selected_assignment=cls.assignment1)
        # cls.pending_dutyswitch_request = DutySwitch.objects.create(status=1, source_assignment=cls.assignment1)


class ScheduleTest(CompleteTestEnvironment, TestCase):
    def test__creation(self):
        schedule = Schedule.objects.create()
        self.assertIsInstance(schedule, Schedule)
        self.assertEqual(schedule.slug, slugify(schedule.name))

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
           side_effect=[x % 2 == 0 for x in range(1, 100)])
    @patch('django.db.models.query.QuerySet.delete', autospec=True)
    def run_and_assert__create_assignments_over_timespan(
            self, mock_queryset_delete, mock_create_assignment,
            schedule: Schedule, start_week: int, end_week: int,
            mode: int, assignments_should_be_deleted: bool, cleaningweeks_should_be_deleted: bool,
            expected_create_assignment_args: list):

        # Mocking create_assignment_directly means we are ignoring the cleaners_per_date property of Schedule
        schedule.create_assignments_over_timespan(start_week, end_week, mode)

        cleaningweek_delete_called = str(mock_queryset_delete.call_args_list).find('CleaningWeek') != -1
        assignment_delete_called = str(mock_queryset_delete.call_args_list).find('Assignment') != -1

        self.assertEqual(assignments_should_be_deleted, assignment_delete_called, msg="mode={}".format(mode))
        self.assertEqual(cleaningweeks_should_be_deleted, cleaningweek_delete_called, msg="mode={}".format(mode))

        args_passed_to_create_assignment = [x[1] for x in [x[0] for x in mock_create_assignment.call_args_list]]

        # Note on [::2] : side_effect of mock_create_assignment causes it to be called twice
        # with the exact same arguments in while loop of create_assignments_over_timespan()
        self.assertListEqual(args_passed_to_create_assignment[::2], expected_create_assignment_args,
                             msg="mode={}".format(mode))

    def test__create_assignments_over_timespan__mode_1(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=1,  # Delete existing Assignments and CleaningDays and regenerate them throughout time frame
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=True, cleaningweeks_should_be_deleted=True,
            expected_create_assignment_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__mode_2(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=2,  # Keep existing Assignments and only create new ones where there are none already
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=False, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__mode_3(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=3,  # Only reassign Assignments on existing CleaningDays, don't generate new CleaningDays
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.end_week,
            assignments_should_be_deleted=True, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_args=[x for x in range(self.start_week, self.end_week+1)])

    def test__create_assignments_over_timespan__only_one_week(self):
        self.run_and_assert__create_assignments_over_timespan(
            mode=2,
            schedule=self.bathroom_schedule, start_week=self.start_week, end_week=self.start_week,
            assignments_should_be_deleted=False, cleaningweeks_should_be_deleted=False,
            expected_create_assignment_args=[self.start_week])

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
