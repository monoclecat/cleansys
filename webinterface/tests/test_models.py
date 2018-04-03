from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

logging.disable(logging.FATAL)


class HelperFunctionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6, starts_days_before_due=1, ends_days_after_due=2)

    def test__correct_dates_to_weekday__date_argument(self):
        self.assertEqual(correct_dates_to_weekday(datetime.date(2010, 2, 1), 3).weekday(), 3)

    def test__correct_dates_to_weekday__list_argument(self):
        corrected_list = correct_dates_to_weekday([datetime.date(2010, 2, 1), datetime.date(2010, 2, 1)], 3)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 3)

    def test__correct_dates_to_weekday__invalid_argument(self):
        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 4))

    def test__correct_dates_to_due_day(self):
        reference_date = datetime.date(2010, 2, 1)  # Has weekday #0
        self.assertEqual(correct_dates_to_due_day(reference_date).weekday(), self.config.date_due)

        corrected_list = correct_dates_to_weekday([reference_date, reference_date], self.config.date_due)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), self.config.date_due)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", self.config.date_due))


class ConfigTest(TestCase):
    def test__creation(self):
        config = Config.objects.create()
        self.assertIsInstance(config, Config)
        self.assertEqual(app_config(), config)

    def test__save(self):
        Config.objects.create(trust_in_users=False)
        another_config = Config.objects.create()
        self.assertIsNone(another_config.pk)

    def test__save__reset_passwords(self):
        config = Config.objects.create(trust_in_users=False)
        with patch.object(Cleaner, "objects") as mock_cleaner_objects:
            config.trust_in_users = True
            config.save()
            self.assertListEqual(mock_cleaner_objects.mock_calls, [call.reset_passwords()])

    def test__timedelta_ends_after_due(self):
        config = Config(date_due=6, starts_days_before_due=1, ends_days_after_due=2)
        timedelta = config.timedelta_ends_after_due()
        self.assertIsInstance(timedelta, datetime.timedelta)
        self.assertEqual(timedelta.days, config.ends_days_after_due)

    def test__timedelta_before_due(self):
        config = Config(date_due=6, starts_days_before_due=1, ends_days_after_due=2)
        timedelta = config.timedelta_before_due()
        self.assertIsInstance(timedelta, datetime.timedelta)
        self.assertEqual(timedelta.days, config.starts_days_before_due)


class ScheduleTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6, starts_days_before_due=1, ends_days_after_due=2)

        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))

        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)
        cls.tool_schedule = Schedule.objects.create(name="tool_schedule", cleaners_per_date=2, frequency=2)
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule, cls.tool_schedule)
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)
        cls.cleaning_day1 = CleaningDay.objects.create(date=correct_dates_to_due_day(datetime.date(2010, 1, 8)),
                                                       schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=correct_dates_to_due_day(datetime.date(2010, 1, 15)),
                                                       schedule=cls.schedule)

        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)

        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)

        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)

    def test__creation(self):
        schedule = Schedule.objects.create()
        self.assertIsInstance(schedule, Schedule)
        self.assertEqual(schedule.slug, slugify(schedule.name))

    def test__str(self):
        self.assertEqual(self.schedule.__str__(), self.schedule.name)

    def test__get_tasks(self):
        task_list = ["firsttask", "secondtask", "thirdtask", "fourthtask"]
        task_string = ','.join(task_list)
        schedule = Schedule(tasks=task_string)
        self.assertEqual(schedule.get_tasks(), task_list)

    def test__cleaners_assigned(self):
        self.assertIn(self.cleaner1, self.schedule.cleaners_assigned())
        self.assertIn(self.cleaner2, self.schedule.cleaners_assigned())

    def test__deployment_ratios__no_cleaners(self):
        schedule = Schedule()
        self.assertListEqual(schedule.deployment_ratios(self.reference_date), [])

    def test__deployment_ratios__cleaners_have_no_assignments(self):
        self.assertListEqual(self.tool_schedule.deployment_ratios(self.reference_date),
                             [[self.cleaner1, 0], [self.cleaner2, 0]])

    def test__deployment_ratios__iterate_over_from_db(self):
        self.assertListEqual(self.schedule.deployment_ratios(self.reference_date),
                             [[self.cleaner2, 1/3], [self.cleaner1, 2/3]])

    def test__deployment_ratios__iterate_over_given(self):
        self.assertListEqual(self.schedule.deployment_ratios(self.reference_date, [self.cleaner1]),
                             [[self.cleaner1, 2/3]])

    def test__get_active_assignments__start_of_date_range(self):
        with patch.object(timezone, 'datetime') as mock_date:
            mock_date.today.return_value = correct_dates_to_due_day(datetime.date(2010, 1, 15)) + \
                datetime.timedelta(days=app_config().ends_days_after_due)
            self.assertListEqual(list(self.schedule.get_active_assignments()), [self.assignment2])

            mock_date.today.return_value = correct_dates_to_due_day(datetime.date(2010, 1, 15)) + \
                datetime.timedelta(days=app_config().ends_days_after_due + 1)
            self.assertListEqual(list(self.schedule.get_active_assignments()), [])

    def test__get_active_assignments__end_of_date_range(self):
        with patch.object(timezone, 'datetime') as mock_date:
            mock_date.today.return_value = correct_dates_to_due_day(datetime.date(2010, 1, 15)) - \
                datetime.timedelta(days=app_config().starts_days_before_due)
            self.assertListEqual(list(self.schedule.get_active_assignments()), [self.assignment2])

            mock_date.today.return_value = correct_dates_to_due_day(datetime.date(2010, 1, 15)) - \
                datetime.timedelta(days=app_config().starts_days_before_due + 1)
            self.assertListEqual(list(self.schedule.get_active_assignments()), [])

    def test__save__frequency_or_cleaners_change(self):
        cleaning_day_date = correct_dates_to_due_day(datetime.date(2010, 1, 22))
        CleaningDay.objects.create(date=cleaning_day_date, schedule=self.schedule)
        with patch.object(Schedule, 'create_assignment') as mock_create_assignment:
            self.schedule.frequency = 1
            self.schedule.save()
            self.assertFalse(self.schedule.cleaningday_set.exists())
            self.assertFalse(self.schedule.assignment_set.exists())
            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(datetime.date(2010, 1, 24)), call(datetime.date(2010, 1, 17)),
                                  call(datetime.date(2010, 1, 10))])

    def test__defined_on_date(self):
        weekly_schedule = Schedule(frequency=1)
        even_week_schedule = Schedule(frequency=2)
        odd_week_schedule = Schedule(frequency=3)

        even_week = datetime.date(2010, 2, 8)
        odd_week = datetime.date(2010, 2, 1)

        self.assertTrue(weekly_schedule.defined_on_date(even_week))
        self.assertTrue(even_week_schedule.defined_on_date(even_week))
        self.assertFalse(odd_week_schedule.defined_on_date(even_week))

        self.assertFalse(even_week_schedule.defined_on_date(odd_week))
        self.assertTrue(odd_week_schedule.defined_on_date(odd_week))

    def test__new_cleaning_duties__keep_existing_assignments(self):
        date1 = datetime.date(2010, 1, 8)
        date2 = datetime.date(2010, 2, 8)

        with patch.object(Schedule, 'create_assignment') as mock_create_assignment:
            self.schedule.new_cleaning_duties(date2, date1, False)
            self.assertIn(self.assignment1, self.schedule.assignment_set.all())
            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(datetime.date(2010, 1, 8)), call(datetime.date(2010, 1, 15)),
                                  call(datetime.date(2010, 1, 22)), call(datetime.date(2010, 1, 29)),
                                  call(datetime.date(2010, 2, 5))])

    def test__new_cleaning_duties__clear_existing_assignments(self):
        date1 = datetime.date(2010, 1, 8)
        date2 = datetime.date(2010, 2, 8)

        with patch.object(Schedule, 'create_assignment') as mock_create_assignment:
            self.schedule.new_cleaning_duties(date2, date1, True)
            self.assertNotIn(self.assignment1, self.schedule.assignment_set.all())
            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(datetime.date(2010, 1, 8)), call(datetime.date(2010, 1, 15)),
                                  call(datetime.date(2010, 1, 22)), call(datetime.date(2010, 1, 29)),
                                  call(datetime.date(2010, 2, 5))])

    def test__create_assignment__not_defined_on_date(self):
        odd_week_schedule = Schedule(frequency=3)
        even_week = datetime.date(2010, 2, 8)
        self.assertIsNone(odd_week_schedule.create_assignment(even_week))

    def test__create_assignment__no_ratios(self):
        even_week = datetime.date(2010, 2, 8)
        self.group.schedules.remove(self.tool_schedule)
        self.assertIsNone(self.tool_schedule.create_assignment(even_week))
        self.group.schedules.add(self.tool_schedule)


class ScheduleGroupTest(TestCase):
    def test__creation(self):
        group = ScheduleGroup.objects.create()
        self.assertIsInstance(group, ScheduleGroup)

    def test__str(self):
        group = ScheduleGroup(name="test")
        self.assertEqual(group.__str__(), group.name)


class CleanerManagerTest(TestCase):
    def test__reset_passwords__users_are_trusted(self):
        Config.objects.create(trust_in_users=True)
        Cleaner.objects.create(name="bob", moved_in=datetime.date(2010, 1, 1), moved_out=datetime.date(2010, 3, 1))
        with patch.object(Cleaner, "user") as mock_user:
            Cleaner.objects.reset_passwords()
            self.assertListEqual(mock_user.mock_calls, [call.set_password('bob')])


class CleanerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6, starts_days_before_due=1, ends_days_after_due=2,
                                           trust_in_users=True)

        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))

        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)
        cls.cleaner = Cleaner.objects.create(name="cleaner1", moved_in=datetime.date(2010, 1, 1),
                                             moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)
        cls.tool_cleaner = Cleaner.objects.create(name="cleaner2", moved_in=datetime.date(2010, 1, 1),
                                                  moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)

        cls.cleaning_day1 = CleaningDay.objects.create(date=correct_dates_to_due_day(datetime.date(2010, 1, 8)),
                                                       schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=correct_dates_to_due_day(datetime.date(2010, 1, 15)),
                                                       schedule=cls.schedule)

        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.tool_cleaner, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)

        cls.rejected_dutyswitch = DutySwitch.objects.create(status=2, source_assignment=cls.assignment1)
        cls.dutyswitch_request_received = DutySwitch.objects.create(source_assignment=cls.assignment2,
                                                                    selected_assignment=cls.assignment1)
        cls.pending_dutyswitch_request = DutySwitch.objects.create(status=1, source_assignment=cls.assignment1)

        cls.dutyswitch1 = DutySwitch.objects.create(status=1, source_assignment=cls.assignment2)
        cls.dutyswitch2 = DutySwitch.objects.create(status=2, source_assignment=cls.assignment2)
        cls.dutyswitch3 = DutySwitch.objects.create(status=0, source_assignment=cls.assignment2)
        cls.dutyswitch4 = DutySwitch.objects.create(status=0, source_assignment=cls.assignment1)

    def test__creation(self):
        cleaner = Cleaner.objects.create(name="bob", moved_in=datetime.date(2010, 1, 1),
                                         moved_out=datetime.date(2010, 3, 1))
        self.assertIsInstance(cleaner, Cleaner)
        self.assertEqual(cleaner.slug, slugify(cleaner.name))

    def test__str(self):
        cleaner = Cleaner(name="bob")
        self.assertEqual(cleaner.__str__(), cleaner.name)

    def test__rejected_dutyswitch_requests(self):
        self.assertListEqual(list(self.cleaner.rejected_dutyswitch_requests()), [self.rejected_dutyswitch])

    def test__dutyswitch_requests_received(self):
        self.assertListEqual(list(self.cleaner.dutyswitch_requests_received()), [self.dutyswitch_request_received])

    def test__pending_dutyswitch_requests(self):
        self.assertListEqual(list(self.cleaner.pending_dutyswitch_requests()), [self.pending_dutyswitch_request])

    def test__nr_assignments_on_day(self):
        self.assertEqual(self.cleaner.nr_assignments_on_day(correct_dates_to_due_day(datetime.date(2010, 1, 8))), 1)
        self.assertEqual(self.cleaner.nr_assignments_on_day(correct_dates_to_due_day(datetime.date(2010, 1, 15))), 0)

    def test__has_pending_requests(self):
        self.assertTrue(self.cleaner.has_pending_requests())

    def test__delete(self):
        cleaner_to_delete = Cleaner.objects.create(name="cleaner_to_delete", moved_in=datetime.date(2010, 1, 1),
                                                   moved_out=datetime.date(2010, 3, 1), schedule_group=self.group)
        user_to_delete = cleaner_to_delete.user
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            cleaner_to_delete.delete()
            self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())
            self.assertListEqual(mock_new_cleaning_duties.mock_calls,
                                 [call(datetime.date(2010, 1, 1), datetime.date(2010, 3, 1))])

    def test__save__no_config_exception(self):
        with patch.object(Config, "objects") as mock_config_objects:
            mock_config_objects.first.return_value = None
            cleaner = Cleaner.objects.create(name="cleaner_to_delete", moved_in=datetime.date(2010, 1, 1),
                                             moved_out=datetime.date(2010, 3, 1), schedule_group=self.group)
            self.assertFalse(cleaner.user.has_usable_password())

    def test__save__slug_changes(self):
        cleaner = Cleaner.objects.create(name="cleaner_original_slug", moved_in=datetime.date(2010, 1, 1),
                                         moved_out=datetime.date(2010, 3, 1), schedule_group=self.group)
        cleaner.name = "cleaner_new_slug"
        with patch.object(User, "set_password") as mock_user_set_pw:
            cleaner.save()
            self.assertEqual(cleaner.user.username, cleaner.slug)
            self.assertListEqual(mock_user_set_pw.mock_calls, [call('cleaner_new_slug')])

    def test__save__moved_out_changes(self):
        old_moved_out = datetime.date(2010, 3, 1)
        new_moved_out = datetime.date(2010, 4, 1)
        cleaner = Cleaner.objects.create(name="cleaner_moved_out_changes", moved_in=datetime.date(2010, 1, 1),
                                         moved_out=old_moved_out, schedule_group=self.group)
        cleaner.moved_out = new_moved_out
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            cleaner.save()
            self.assertListEqual(mock_new_cleaning_duties.mock_calls,
                                 [call(correct_dates_to_due_day(old_moved_out),
                                       correct_dates_to_due_day(new_moved_out), True)])

    def test__save__moved_in_changes(self):
        old_moved_in = datetime.date(2010, 1, 1)
        new_moved_in = datetime.date(2010, 2, 1)
        cleaner = Cleaner.objects.create(name="cleaner_moved_in_changes", moved_in=old_moved_in,
                                         moved_out=datetime.date(2010, 3, 1), schedule_group=self.group)
        cleaner.moved_in = new_moved_in
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            cleaner.save()
            self.assertListEqual(mock_new_cleaning_duties.mock_calls,
                                 [call(correct_dates_to_due_day(old_moved_in),
                                       correct_dates_to_due_day(new_moved_in), True)])

    def test__save__group_changes_with_previous_group(self):
        cleaner = Cleaner.objects.create(name="cleaner_group_changes", moved_in=datetime.date(2010, 1, 1),
                                         moved_out=datetime.date(2010, 3, 1), schedule_group=self.group)

        schedule_of_new_group = Schedule.objects.create(name="new_group_schedule", cleaners_per_date=2, frequency=2)
        new_group = ScheduleGroup.objects.create(name="new_group")
        new_group.schedules.add(schedule_of_new_group)

        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            cleaner.schedule_group = new_group
            cleaner.save()
            self.assertListEqual(mock_new_cleaning_duties.mock_calls,
                                 [call(correct_dates_to_due_day(cleaner.moved_in),
                                       correct_dates_to_due_day(cleaner.moved_out)),
                                  call(correct_dates_to_due_day(cleaner.moved_in),
                                       correct_dates_to_due_day(cleaner.moved_out))])

    def test__save__group_changes_no_previous_group(self):
        cleaner = Cleaner.objects.create(name="cleaner_group_changes_no_prev", moved_in=datetime.date(2010, 1, 1),
                                         moved_out=datetime.date(2010, 3, 1))

        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            cleaner.schedule_group = self.group
            cleaner.save()
            self.assertListEqual(mock_new_cleaning_duties.mock_calls,
                                 [call(correct_dates_to_due_day(cleaner.moved_in),
                                       correct_dates_to_due_day(cleaner.moved_out))])


class AssignmentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6, starts_days_before_due=1, ends_days_after_due=2,
                                           trust_in_users=True)

        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))

        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1))
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1))
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1))

        cls.cleaning_day1 = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=cls.reference_date + datetime.timedelta(days=7),
                                                       schedule=cls.schedule)

        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)

        cls.task1 = Task.objects.create(name="task1", cleaned_by=cls.assignment1)
        cls.task2 = Task.objects.create(name="task1", cleaned_by=cls.assignment2)

    def test__creation(self):
        assignment = Assignment.objects.create(cleaner=self.cleaner1, schedule=self.schedule,
                                               cleaning_day=self.cleaning_day1)
        self.assertIsInstance(assignment, Assignment)

    def test__str(self):
        self.assertIn(self.schedule.name, self.assignment1.__str__())
        self.assertIn(self.cleaner1.name, self.assignment1.__str__())
        self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), self.assignment1.__str__())

    def test__cleaners_on_day_for_schedule(self):
        self.assertListEqual(list(self.assignment1.cleaners_on_date_for_schedule()), [self.cleaner1, self.cleaner2])

    def test__possible_start_date(self):
        self.assertEqual(self.assignment1.possible_start_date(),
                         self.reference_date - datetime.timedelta(days=self.config.starts_days_before_due))

    def test__cleaning_buddies(self):
        self.assertListEqual(list(self.assignment1.cleaning_buddies()), [self.cleaner2])

    def test__tasks_cleaned(self):
        self.assertListEqual(list(self.assignment1.tasks_cleaned()), [self.task1])


class TaskTest(TestCase):
    def test__creation(self):
        task = Task.objects.create(name="task1")
        self.assertIsInstance(task, Task)

    def test__str(self):
        task = Task(name="task1")
        self.assertEqual(task.name, task.__str__())


class CleaningDayTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_date = datetime.date(2010, 1, 8)
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2, tasks="task1, task2")
        cls.cleaning_day = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)

    def test__creation(self):
        cleaning_day = CleaningDay.objects.create(date=datetime.date(2010, 2, 8), schedule=self.schedule)
        self.assertIsInstance(cleaning_day, CleaningDay)

    def test__str(self):
        self.assertIn(self.schedule.name, self.cleaning_day.__str__())
        self.assertIn(self.cleaning_day.date.strftime('%d-%b-%Y'), self.cleaning_day.__str__())

    def test__initiate_tasks(self):
        self.cleaning_day.initiate_tasks()
        self.assertListEqual(list(Task.objects.all()), list(self.cleaning_day.task_set.all()))
        self.assertTrue(self.cleaning_day.task_set.filter(name="task1").exists())
        self.assertTrue(self.cleaning_day.task_set.filter(name="task2").exists())

    def test__delete(self):
        cleaning_day = CleaningDay.objects.create(date=datetime.date(2010, 3, 8), schedule=self.schedule)
        cleaning_day.initiate_tasks()
        cleaning_day.delete()
        self.assertFalse(Task.objects.filter(name="task1").exists())
        self.assertFalse(Task.objects.filter(name="task2").exists())


class DutySwitchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6, starts_days_before_due=1, ends_days_after_due=2,
                                           trust_in_users=True)

        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))

        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3", moved_in=datetime.date(2010, 1, 1),
                                              moved_out=datetime.date(2010, 3, 1), schedule_group=cls.group)

        cls.cleaning_day1 = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(
            date=cls.reference_date + datetime.timedelta(days=7), schedule=cls.schedule)
        cls.cleaning_day3 = CleaningDay.objects.create(
            date=cls.reference_date + datetime.timedelta(days=14), schedule=cls.schedule)

        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule,
            cleaning_day=cls.cleaning_day2)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule,
            cleaning_day=cls.cleaning_day3)

        cls.switch_1 = DutySwitch.objects.create(source_assignment=cls.assignment1)
        cls.switch_1_with_2 = DutySwitch.objects.create(
            source_assignment=cls.assignment1, selected_assignment=cls.assignment2, status=1)

    def test__creation(self):
        duty_switch = DutySwitch.objects.create(source_assignment=self.assignment1)
        self.assertIsInstance(duty_switch, DutySwitch)

    def test__str__with_selected(self):
        string = self.switch_1_with_2.__str__()
        self.assertIn(self.assignment1.cleaner.name, string)
        self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), string)
        self.assertIn(self.assignment2.cleaner.name, string)
        self.assertIn(self.assignment2.cleaning_day.date.strftime('%d-%b-%Y'), string)
        self.assertIn(str(self.switch_1_with_2.status), string)

    def test__str__none_selected(self):
        string = self.switch_1.__str__()
        self.assertIn(self.assignment1.cleaner.name, string)
        self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), string)
        self.assertIn(str(self.switch_1.status), string)

    def test__filtered_destinations(self):
        duty_switch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2)
        duty_switch.destinations.add(self.assignment1, self.assignment2, self.assignment3)
        self.assertListEqual(list(duty_switch.filtered_destinations()), [self.assignment3])

    def test__set_selected(self):
        duty_switch = DutySwitch.objects.create(source_assignment=self.assignment1)
        duty_switch.set_selected(self.assignment2)
        self.assertEqual(duty_switch.selected_assignment, self.assignment2)
        self.assertEqual(duty_switch.status, 1)

    def test__selected_was_cancelled(self):
        duty_switch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
        duty_switch.selected_was_cancelled()
        self.assertIsNone(duty_switch.selected_assignment)
        self.assertEqual(duty_switch.status, 0)

    def test__selected_was_rejected(self):
        duty_switch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
        duty_switch.selected_was_rejected()
        self.assertIsNone(duty_switch.selected_assignment)
        self.assertEqual(duty_switch.status, 2)

    def test__selected_was_accepted(self):
        reference_date = correct_dates_to_due_day(datetime.date(2010, 4, 1))
        assignment1_date = reference_date
        assignment2_date = reference_date + datetime.timedelta(days=7)
        assignment3_date = reference_date + datetime.timedelta(days=14)

        cleaning_day1 = CleaningDay.objects.create(date=assignment1_date, schedule=self.schedule)
        cleaning_day2 = CleaningDay.objects.create(date=assignment2_date, schedule=self.schedule)
        cleaning_day3 = CleaningDay.objects.create(date=assignment3_date, schedule=self.schedule)

        assignment1 = Assignment.objects.create(
            cleaner=self.cleaner1, schedule=self.schedule, cleaning_day=cleaning_day1)
        assignment2 = Assignment.objects.create(
            cleaner=self.cleaner2, schedule=self.schedule, cleaning_day=cleaning_day2)
        assignment3 = Assignment.objects.create(
            cleaner=self.cleaner3, schedule=self.schedule, cleaning_day=cleaning_day3)

        # On these the function selected_was_rejected() will be called
        assignment1__is__selected_assignment = DutySwitch.objects.create(
            source_assignment=assignment3, selected_assignment=assignment1, status=1)
        assignment2__is__selected_assignment = DutySwitch.objects.create(
            source_assignment=assignment3, selected_assignment=assignment2, status=1)

        # These will be deleted
        assignment1__is__source_assignment = DutySwitch.objects.create(source_assignment=assignment1, status=0)
        assignment2__is__source_assignment = DutySwitch.objects.create(source_assignment=assignment2, status=0)

        duty_switch = DutySwitch.objects.create(source_assignment=assignment1, selected_assignment=assignment2)

        duty_switch.selected_was_accepted()

        self.assertIn(assignment1.cleaner, cleaning_day1.excluded.all())
        self.assertNotIn(assignment2.cleaner, cleaning_day1.excluded.all())

        self.assertEqual(assignment1.cleaning_day.date, assignment2_date)
        self.assertEqual(assignment2.cleaning_day.date, assignment1_date)

        self.assertEqual(DutySwitch.objects.get(pk=assignment1__is__selected_assignment.pk).status, 2)
        self.assertEqual(DutySwitch.objects.get(pk=assignment2__is__selected_assignment.pk).status, 2)

        self.assertFalse(DutySwitch.objects.filter(pk=assignment1__is__source_assignment.pk).exists())
        self.assertFalse(DutySwitch.objects.filter(pk=assignment2__is__source_assignment.pk).exists())
        self.assertFalse(DutySwitch.objects.filter(pk=duty_switch.pk).exists())
