from django.test import TestCase
from webinterface.models import *


class AssignmentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_week = 2500

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1")
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2")
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_week1 = CleaningWeek.objects.create(week=cls.reference_week, schedule=cls.schedule)
        cls.cleaning_week2 = CleaningWeek.objects.create(week=cls.reference_week + 1, schedule=cls.schedule)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_week=cls.cleaning_week1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_week=cls.cleaning_week1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_week=cls.cleaning_week2)

        # DutySwitch
        cls.dutyswitch = DutySwitch.objects.create(requester_assignment=cls.assignment1)

    def test__str(self):
        self.assertIn(self.schedule.name, self.assignment1.__str__())
        self.assertIn(self.cleaner1.name, self.assignment1.__str__())
        self.assertIn(self.assignment1.assignment_date().strftime('%d-%b-%Y'), self.assignment1.__str__())

    def test__all_cleaners_in_week_for_schedule(self):
        all_cleaners = self.assignment1.all_cleaners_in_week_for_schedule()
        self.assertIn(self.cleaner1, all_cleaners)
        self.assertIn(self.cleaner2, all_cleaners)
        self.assertNotIn(self.cleaner3, all_cleaners)

    def test__other_cleaners_in_week_for_schedule(self):
        other_cleaners = self.assignment1.other_cleaners_in_week_for_schedule()
        self.assertNotIn(self.cleaner1, other_cleaners)
        self.assertIn(self.cleaner2, other_cleaners)
        self.assertNotIn(self.cleaner3, other_cleaners)

    def test__switch_requested(self):
        self.assertEqual(self.assignment1.switch_requested(), self.dutyswitch)
        self.assertEqual(self.assignment2.switch_requested(), None)
