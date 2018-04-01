from django.test import TestCase
from webinterface.models import *
import random
import logging, traceback, sys
from unittest.mock import *

logging.disable(logging.WARNING)


def test_config():
    return Config(date_due=1, starts_days_before_due=1, ends_days_after_due=2)


mock_config_model = Mock()
mock_config_model.objects.first.return_value = test_config()


class HelperFunctionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = test_config().save()

    def test__correct_dates_to_weekday__date_argument(self):
        self.assertEqual(correct_dates_to_weekday(datetime.date(2010, 2, 1), 3).weekday(), 3)

    def test__correct_dates_to_weekday__list_argument(self):
        corrected_list = correct_dates_to_weekday([datetime.date(2010, 2, 1), datetime.date(2010, 2, 1)], 3)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 3)

    def test__correct_dates_to_weekday__invalid_argument(self):
        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 4))

    def test_correct_dates_to_due_day(self):
        reference_date = datetime.date(2010, 2, 1)  # Has weekday #0
        self.assertEqual(correct_dates_to_due_day(reference_date).weekday(), test_config().date_due)

        corrected_list = correct_dates_to_weekday([reference_date, reference_date], test_config().date_due)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), test_config().date_due)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", test_config().date_due))


class ConfigTest(TestCase):
    def test_creation(self):
        config = Config.objects.create()
        self.assertIsInstance(config, Config)
        self.assertEqual(app_config(), config)

    def test_save(self):
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
        config = test_config()
        timedelta = config.timedelta_ends_after_due()
        self.assertIsInstance(timedelta, datetime.timedelta)
        self.assertEqual(timedelta.days, config.ends_days_after_due)

    def test__timedelta_before_due(self):
        config = test_config()
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

        cls.assignment1 = Assignment.\
            objects.create(cleaner=cls.cleaner1, date=correct_dates_to_due_day(datetime.date(2010, 1, 8)),
                           schedule=cls.schedule)

        cls.assignment2 = Assignment.\
            objects.create(cleaner=cls.cleaner1, date=correct_dates_to_due_day(datetime.date(2010, 1, 15)),
                           schedule=cls.schedule)

        cls.assignment3 = Assignment.\
            objects.create(cleaner=cls.cleaner2, date=correct_dates_to_due_day(datetime.date(2010, 1, 8)),
                           schedule=cls.schedule)

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

    def test_cleaners_assigned(self):
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
        cleaning_day_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        CleaningDay.objects.create(date=cleaning_day_date, schedule=self.schedule)
        with patch.object(Schedule, 'assign_cleaning_duty') as mock_assign_cleaning_duty:
            self.schedule.frequency = 1
            self.schedule.save()
            self.assertFalse(self.schedule.cleaningday_set.exists())
            self.assertFalse(self.schedule.assignment_set.exists())
            self.assertListEqual(mock_assign_cleaning_duty.mock_calls, [call(datetime.date(2010, 1, 10))])

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

        with patch.object(Schedule, 'assign_cleaning_duty') as mock_assign_cleaning_duty:
            self.schedule.new_cleaning_duties(date2, date1, False)
            self.assertIn(self.assignment1, self.schedule.assignment_set.all())
            self.assertListEqual(mock_assign_cleaning_duty.mock_calls,
                                 [call(datetime.date(2010, 1, 8)), call(datetime.date(2010, 1, 15)),
                                  call(datetime.date(2010, 1, 22)), call(datetime.date(2010, 1, 29)),
                                  call(datetime.date(2010, 2, 5))])

    def test__new_cleaning_duties__clear_existing_assignments(self):
        date1 = datetime.date(2010, 1, 8)
        date2 = datetime.date(2010, 2, 8)

        with patch.object(Schedule, 'assign_cleaning_duty') as mock_assign_cleaning_duty:
            self.schedule.new_cleaning_duties(date2, date1, True)
            self.assertNotIn(self.assignment1, self.schedule.assignment_set.all())
            self.assertListEqual(mock_assign_cleaning_duty.mock_calls,
                                 [call(datetime.date(2010, 1, 8)), call(datetime.date(2010, 1, 15)),
                                  call(datetime.date(2010, 1, 22)), call(datetime.date(2010, 1, 29)),
                                  call(datetime.date(2010, 2, 5))])







