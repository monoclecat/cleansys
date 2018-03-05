from django.test import TestCase
from webinterface.models import *
import random
import logging
from unittest.mock import *

logging.disable(logging.WARNING)

reference_date = datetime.date(2010, 2, 1)  # Has weekday #0


def test_config():
    return Config(date_due=1, starts_days_before_due=1, ends_days_after_due=2)


mock_config_model = Mock()
mock_config_model.objects.first.return_value = test_config()


class HelperFunctionsTest(TestCase):
    def test_correct_dates_to_due_day(self):
        self.assertEqual(correct_dates_to_weekday(reference_date, 3).weekday(), 3)

        corrected_list = correct_dates_to_weekday([reference_date, reference_date], 3)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 3)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 4))

    @patch("webinterface.models.Config", mock_config_model)
    def test_correct_dates_to_due_day(self):
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
        Config.objects.create()
        another_config = Config.objects.create()
        self.assertIsNone(another_config.pk)

    def test_timedelta_ends_after_due(self):
        config = test_config()
        timedelta = config.timedelta_ends_after_due()
        self.assertIsInstance(timedelta, datetime.timedelta)
        self.assertEqual(timedelta.days, config.ends_days_after_due)

    def test_timedelta_before_due(self):
        config = test_config()
        timedelta = config.timedelta_before_due()
        self.assertIsInstance(timedelta, datetime.timedelta)
        self.assertEqual(timedelta.days, config.starts_days_before_due)


# REDONE UNTIL HERE


class ScheduleTest(TestCase):
    @staticmethod
    @patch("webinterface.models.Config", mock_config_model)
    def create_schedule(name="Lick floor1", cleaners_per_date=2, frequency=1):
        iterator = 2
        while Schedule.objects.filter(name=name).exists():
            name = name[:-1] + str(iterator)
            iterator += 1
        return Schedule.objects.create(name=name, cleaners_per_date=cleaners_per_date, frequency=frequency)

    @staticmethod
    def create_schedules_with_cleaners(name="Lick floor1", cleaners_per_date=2, frequency=2, nr_cleaners=4,
                                       nr_schedules=1, group=None):
        """Creates a number of schedules that have are assigned to the same group and share the same cleaners."""
        schedules = []
        if not group:
            group = ScheduleGroupTest.create_schedulegroup()

        for i in range(nr_schedules):
            schedule = ScheduleTest.create_schedule(name=name, cleaners_per_date=cleaners_per_date, frequency=frequency)
            group.schedules.add(schedule)
            schedules.append(schedule)

        for i in range(nr_cleaners):
            cleaner = CleanerTest.create_cleaner()
            cleaner.schedule_group = group
            cleaner.save()

        return schedules

    def test_creation(self):
        schedule = self.create_schedule()
        self.assertIsInstance(schedule, Schedule)
        self.assertEqual(schedule.slug, slugify(schedule.name))

    def test_str(self):
        schedule = Schedule(name="dog")
        self.assertEqual(schedule.__str__(), schedule.name)

    def test_get_tasks(self):
        task_list = ["firsttask", "secondtask", "thirdtask", "fourthtask"]
        task_string = ','.join(task_list)
        schedule = Schedule(tasks=task_string)
        self.assertEqual(schedule.get_tasks(), task_list)

    def test_cleaners_assigned(self):
        cleaners = [CleanerTest.create_cleaner() for i in range(4)]

        group1 = ScheduleGroupTest.create_schedulegroup()
        group2 = ScheduleGroupTest.create_schedulegroup()

        comp_list = list()
        for cleaner in cleaners:
            if random.randint(1, 2) == 1:
                cleaner.schedule_group = group1
                comp_list.append({'id': cleaner.pk})
            else:
                cleaner.schedule_group = group2
            cleaner.save()

        schedule1 = ScheduleTest.create_schedule()
        schedule2 = ScheduleTest.create_schedule()

        group1.schedules.add(schedule1, schedule2)
        group2.schedules.add(schedule2)

        assigned_cleaners = schedule1.cleaners_assigned()
        self.assertListEqual(list(assigned_cleaners.all().values('id')), comp_list)

    def test_deployment_ratios(self):
        schedule_no_cleaner = ScheduleTest.create_schedule()
        self.assertListEqual(schedule_no_cleaner.deployment_ratios(reference_date), [])

        schedule = ScheduleTest.create_schedules_with_cleaners()[0]
        cleaners = []
        for cleaner, ratio in schedule.deployment_ratios(reference_date):
            cleaners.append(cleaner)
        for cleaner in schedule.cleaners_assigned():
            self.assertIn(cleaner, cleaners)
        cleaners = []
        for cleaner, ratio in schedule.deployment_ratios(reference_date, cleaners=schedule.cleaners_assigned()[:2]):
            cleaners.append(cleaner)
        for cleaner in schedule.cleaners_assigned()[:2]:
            self.assertIn(cleaner, cleaners)
        for cleaner in schedule.cleaners_assigned()[2:]:
            self.assertNotIn(cleaner, cleaners)

    def test_assign_cleaning_duty(self):
        schedule = ScheduleTest.create_schedule(frequency=2, cleaners_per_date=2)  # Even weeks

        odd_date = reference_date  # Is an odd week
        self.assertIsNone(schedule.assign_cleaning_duty(odd_date))

        even_date = odd_date + datetime.timedelta(days=7)  # Is an even week
        self.assertIsNone(schedule.assign_cleaning_duty(even_date))  # No Cleaners are assigned

        print(Schedule.objects.all())
        schedule1, schedule2, schedule3 = ScheduleTest.create_schedules_with_cleaners(nr_schedules=3, nr_cleaners=2)
        print(schedule1.assignment_set.all())
        print(schedule1.cleaners_assigned().values('moved_in'))
        print(schedule1.cleaners_assigned().values('moved_out'))
        print(schedule1.cleaners_assigned().all())
        schedule1.assign_cleaning_duty(even_date)
        created_assignments = schedule1.assignment_set.filter(date=even_date)
        self.assertEqual(created_assignments.count(), schedule1.cleaners_per_date)

        schedule2.assign_cleaning_duty(even_date)  # All Cleaners will already be assigned once on date
        created_assignments = schedule2.assignment_set.filter(date=even_date)
        self.assertEqual(created_assignments.count(), schedule2.cleaners_per_date)

        schedule3.assign_cleaning_duty(even_date)  # All Cleaners will already be assigned twice on date
        created_assignments = schedule3.assignment_set.filter(date=even_date)
        self.assertEqual(created_assignments.count(), schedule3.cleaners_per_date)

    def test_get_active_assignments(self):
        schedule = ScheduleTest.create_schedules_with_cleaners(nr_schedules=1, nr_cleaners=2)[0]

        latest_assignments = schedule.get_active_assignments()
        self.assertEqual(latest_assignments.count(), schedule.cleaners_per_date)

    def test_save(self):
        schedule = ScheduleTest.create_schedules_with_cleaners(nr_schedules=1, nr_cleaners=2)[0]
        assignment = schedule.assignment_set.first()
        cleaningday = schedule.cleaningday_set.first()

        schedule.cleaners_per_date = schedule.cleaners_per_date + 1
        schedule.save()
        self.assertNotIn(assignment, schedule.assignment_set.all())
        self.assertNotIn(cleaningday, schedule.cleaningday_set.all())


class CleanerTest(TestCase):
    @staticmethod
    @patch("webinterface.models.Config", mock_config_model)
    def create_cleaner(name="Bob1"):
        iterator = 2
        delta_moved_in = 0
        delta_moved_out = 14
        while Cleaner.objects.filter(name=name).exists():
            name = name[:-1] + str(iterator)
            # delta_moved_in -= 100
            # delta_moved_out -= 100
            iterator += 1
        return Cleaner.objects.create(name=name,
                                      moved_in=reference_date + timezone.timedelta(days=delta_moved_in),
                                      moved_out=reference_date + timezone.timedelta(days=delta_moved_out))

    def test_creation(self):
        cleaner = self.create_cleaner()
        self.assertIsInstance(cleaner, Cleaner)
        self.assertEqual(cleaner.__str__(), cleaner.name)
        self.assertEqual(cleaner.slug, slugify(cleaner.name))

    def test_dutyswitch_request_functions(self):
        schedule = ScheduleTest.create_schedules_with_cleaners(nr_schedules=1, nr_cleaners=1)[0]
        cleaner = schedule.cleaners_assigned().first()
        self.assertEqual(cleaner.has_pending_requests(), False)
        dutyswith = DutySwitchTest.create_dutyswitch(schedule.assignment_set.first())
        dutyswith.status = 1
        dutyswith.save()
        self.assertEqual(cleaner.pending_dutyswitch_requests().first(), dutyswith)
        self.assertEqual(cleaner.has_pending_requests(), True)
        dutyswith.status = 2
        dutyswith.save()
        self.assertEqual(cleaner.rejected_dutyswitch_requests().first(), dutyswith)

        dutyswith.selected_assignment = schedule.assignment_set.first()
        dutyswith.save()
        self.assertEqual(cleaner.dutyswitch_requests_received().first(), dutyswith)

    def test_delete(self):
        schedule1, schedule2 = ScheduleTest.create_schedules_with_cleaners(nr_schedules=2, nr_cleaners=2)
        cleaner = schedule1.cleaners_assigned().first()
        cleaner.delete()
        self.assertNotIn(cleaner, Assignment.objects.filter(cleaner=cleaner))


class AssignmentTest(TestCase):
    @staticmethod
    def create_assignment(cleaner=None, date=reference_date, schedule=None):
        if not cleaner:
            cleaner = CleanerTest.create_cleaner()
        if not schedule:
            schedule = ScheduleTest.create_schedule()
        return Assignment.objects.create(cleaner=cleaner, date=date, schedule=schedule)

    def test_creation(self):
        assignment = self.create_assignment()
        self.assertIsInstance(assignment, Assignment)
        self.assertEqual(assignment.__str__(), assignment.schedule.name + ": " +
                         assignment.cleaner.name + " on the " + str(assignment.date))


class DutySwitchTest(TestCase):
    @staticmethod
    def create_dutyswitch(source_assignment=AssignmentTest.create_assignment(), status=0):
        return DutySwitch.objects.create(source_assignment=source_assignment, status=status)

    def test_creation(self):
        dutyswitch = self.create_dutyswitch()
        self.assertIsInstance(dutyswitch, DutySwitch)
        self.assertEqual(dutyswitch.__str__(), "Source assignment: " + str(dutyswitch.source_assignment))


class CleaningDayTest(TestCase):
    @staticmethod
    def create_cleaningday(date=timezone.now().date(), schedule=ScheduleTest.create_schedule()):
        return CleaningDay.objects.create(date=date, schedule=schedule)

    def test_creation(self):
        cleaningday = self.create_cleaningday()
        self.assertIsInstance(cleaningday, CleaningDay)


class ScheduleGroupTest(TestCase):
    @staticmethod
    def create_schedulegroup(name="Bob1"):
        iterator = 2
        while ScheduleGroup.objects.filter(name=name).exists():
            name = name[:-1] + str(iterator)
            iterator += 1
        return ScheduleGroup.objects.create(name=name)

    def test_creation(self):
        schedulegroup = self.create_schedulegroup()
        self.assertIsInstance(schedulegroup, ScheduleGroup)
        self.assertEqual(schedulegroup.__str__(), schedulegroup.name)
