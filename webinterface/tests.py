from django.test import TestCase
from .models import *


class HelperFunctionsTest(TestCase):
    def test_correct_dates_to_weekday(self):
        date = datetime.date(2016, 1, 1)
        for add_day in range(6):
            for wanted_day in range(6):
                self.assertEqual(correct_dates_to_weekday(date + datetime.timedelta(days=add_day),
                                                          wanted_day).weekday(), wanted_day)
        for add_day in range(6):
            for wanted_day in range(6):
                corrected_list = correct_dates_to_weekday(
                    [date + datetime.timedelta(days=add_day), date + datetime.timedelta(days=add_day)],
                    wanted_day)
                self.assertIsInstance(corrected_list, list)
                self.assertEqual(corrected_list[0].weekday(), wanted_day)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 4))


def create_cleaner(name="Bob1"):
    iterator = 2
    delta_moved_in = 0
    delta_moved_out = 900
    while Cleaner.objects.filter(name=name).exists():
        name = name[:-1] + str(iterator)
        delta_moved_in -= 100
        delta_moved_out -= 100
        iterator += 1
    return Cleaner.objects.create(name=name, moved_in=datetime.date.today() + datetime.timedelta(days=delta_moved_in),
                                  moved_out=datetime.date.today() + datetime.timedelta(days=delta_moved_out))


def create_schedule(name="Lick floor1", cleaners_per_date=2, frequency=2):
    iterator = 2
    while Schedule.objects.filter(name=name).exists():
        name = name[:-1] + str(iterator)
        iterator += 1
    return Schedule.objects.create(name=name, cleaners_per_date=cleaners_per_date, frequency=frequency)


def create_assignment(cleaner=create_cleaner(), date=datetime.date.today(), schedule=create_schedule()):
    return Assignment.objects.create(cleaner=cleaner, date=date, schedule=schedule)


def create_dutyswitch(source_assignment=create_assignment(), status=0):
    return DutySwitch.objects.create(source_assignment=source_assignment, status=status)


def create_cleaningday(date=datetime.date.today(), schedule=create_schedule()):
    return CleaningDay.objects.create(date=date, schedule=schedule)


def create_schedulegroup(name="Bob1"):
    iterator = 2
    while ScheduleGroup.objects.filter(name=name).exists():
        name = name[:-1] + str(iterator)
        iterator += 1
    return ScheduleGroup.objects.create(name=name)


class ScheduleTest(TestCase):
    def test_creation(self):
        schedule = create_schedule()
        self.assertIsInstance(schedule, Schedule)
        self.assertEqual(schedule.__str__(), schedule.name)
        self.assertEqual(schedule.slug, slugify(schedule.name))

    def test_get_tasks(self):
        task_list = ["firsttask", "secondtask", "thirdtask", "fourthtask"]
        task_string = ','.join(task_list)
        schedule = create_schedule()
        schedule.tasks = task_string
        self.assertEqual(schedule.get_tasks(), task_list)


class CleanerTest(TestCase):
    def test_creation(self):
        cleaner = create_cleaner()
        self.assertIsInstance(cleaner, Cleaner)
        self.assertEqual(cleaner.__str__(), cleaner.name)
        self.assertEqual(cleaner.slug, slugify(cleaner.name))


class AssignmentTest(TestCase):
    def test_creation(self):
        assignment = create_assignment()
        self.assertIsInstance(assignment, Assignment)
        self.assertEqual(assignment.__str__(), assignment.schedule.name + ": " +
                         assignment.cleaner.name + " on the " + str(assignment.date))


class DutySwitchTest(TestCase):
    def test_creation(self):
        dutyswitch = create_dutyswitch()
        self.assertIsInstance(dutyswitch, DutySwitch)
        self.assertEqual(dutyswitch.__str__(), "Source assignment: "+str(dutyswitch.source_assignment))


class CleaningDayTest(TestCase):
    def test_creation(self):
        cleaningday = create_cleaningday()
        self.assertIsInstance(cleaningday, CleaningDay)


class ScheduleGroupTest(TestCase):
    def test_creation(self):
        schedulegroup = create_schedulegroup()
        self.assertIsInstance(schedulegroup, ScheduleGroup)
        self.assertEqual(schedulegroup.__str__(), schedulegroup.name)

