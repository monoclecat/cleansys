from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


# class DutySwitchTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         # Config
#         cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
#         cls.one_week = datetime.timedelta(days=7)
#
#         # Schedule
#         cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)
#
#         # ScheduleGroup
#         cls.group = ScheduleGroup.objects.create(name="group")
#         cls.group.schedules.add(cls.schedule)
#
#         # Cleaners
#         cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
#         cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=1)
#         cls.cleaner3 = Cleaner.objects.create(name="cleaner3", preference=1)
#
#         # Affiliations
#         cls.cl1_affil = Affiliation.objects.create(
#             cleaner=cls.cleaner1, group=cls.group, beginning=cls.reference_date,
#             end=cls.reference_date + 4 * cls.one_week)
#         cls.cl2_affil = Affiliation.objects.create(
#             cleaner=cls.cleaner2, group=cls.group, beginning=cls.reference_date,
#             end=cls.reference_date + 4 * cls.one_week)
#         cls.cl3_affil = Affiliation.objects.create(
#             cleaner=cls.cleaner3, group=cls.group, beginning=cls.reference_date,
#             end=cls.reference_date + 4 * cls.one_week)
#
#         # CleaningDays
#         cls.cleaning_day1 = CleaningWeek.objects.create(date=cls.reference_date, schedule=cls.schedule)
#         cls.cleaning_day2 = CleaningWeek.objects.create(date=cls.reference_date + cls.one_week, schedule=cls.schedule)
#         cls.cleaning_day3 = CleaningWeek.objects.create(
#             date=cls.reference_date + 2 * cls.one_week, schedule=cls.schedule)
#
#         # Assignments
#         cls.assignment1 = Assignment.objects.create(
#             cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
#         cls.assignment2 = Assignment.objects.create(
#             cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
#         cls.assignment3 = Assignment.objects.create(
#             cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_day=cls.cleaning_day3)
#
#         # DutySwitch requests
#         cls.switch_1 = DutySwitch.objects.create(source_assignment=cls.assignment1)
#         cls.switch_1_with_2 = DutySwitch.objects.create(
#             source_assignment=cls.assignment1, selected_assignment=cls.assignment2, status=1)
#
#     def test__creation(self):
#         duty_switch = DutySwitch.objects.create(source_assignment=self.assignment1)
#         self.assertIsInstance(duty_switch, DutySwitch)
#
#     def test__str__with_selected(self):
#         string = self.switch_1_with_2.__str__()
#         self.assertIn(self.assignment1.cleaner.name, string)
#         self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), string)
#         self.assertIn(self.assignment2.cleaner.name, string)
#         self.assertIn(self.assignment2.cleaning_day.date.strftime('%d-%b-%Y'), string)
#         self.assertIn(str(self.switch_1_with_2.status), string)
#
#     def test__str__none_selected(self):
#         string = self.switch_1.__str__()
#         self.assertIn(self.assignment1.cleaner.name, string)
#         self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), string)
#         self.assertIn(str(self.switch_1.status), string)
#
#     def test__destinations_without_source_and_selected(self):
#         self.switch_1_with_2.destinations.add(self.assignment1, self.assignment2, self.assignment3)
#         destinations = self.switch_1_with_2.destinations_without_source_and_selected()
#         self.assertNotIn(self.assignment1, destinations)
#         self.assertNotIn(self.assignment2, destinations)
#         self.assertIn(self.assignment3, destinations)
#
#     def test__set_selected(self):
#         self.switch_1.set_selected(self.assignment2)
#         self.assertEqual(self.switch_1.selected_assignment, self.assignment2)
#         self.assertEqual(self.switch_1.status, 1)
#
#     def test__selected_was_accepted(self):
#         # On these the function selected_was_rejected() will be called
#         assignment1__is__selected_assignment = DutySwitch.objects.create(
#             source_assignment=self.assignment3, selected_assignment=self.assignment1, status=1)
#         assignment2__is__selected_assignment = DutySwitch.objects.create(
#             source_assignment=self.assignment3, selected_assignment=self.assignment2, status=1)
#
#         # These will be deleted
#         assignment1__is__source_assignment = DutySwitch.objects.create(source_assignment=self.assignment1, status=0)
#         assignment2__is__source_assignment = DutySwitch.objects.create(source_assignment=self.assignment2, status=0)
#
#         old_assignment_1_date = self.assignment1.cleaning_day.date
#         old_assignment_2_date = self.assignment2.cleaning_day.date
#
#         dutyswitch = DutySwitch.objects.create(
#             source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
#         dutyswitch.selected_was_accepted()
#
#         self.assertIn(self.assignment1.cleaner, self.cleaning_day1.excluded.all())
#         self.assertNotIn(self.assignment2.cleaner, self.cleaning_day1.excluded.all())
#
#         self.assertEqual(self.assignment1.cleaning_day.date, old_assignment_2_date)
#         self.assertEqual(self.assignment2.cleaning_day.date, old_assignment_1_date)
#
#         self.assertEqual(DutySwitch.objects.get(pk=assignment1__is__selected_assignment.pk).status, 2)
#         self.assertEqual(DutySwitch.objects.get(pk=assignment2__is__selected_assignment.pk).status, 2)
#
#         self.assertFalse(DutySwitch.objects.filter(pk=assignment1__is__source_assignment.pk).exists())
#         self.assertFalse(DutySwitch.objects.filter(pk=assignment2__is__source_assignment.pk).exists())
#         self.assertFalse(DutySwitch.objects.filter(pk=self.switch_1_with_2.pk).exists())
#
#     def test__selected_was_cancelled(self):
#         dutyswitch = DutySwitch.objects.create(
#             source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
#         dutyswitch.selected_was_cancelled()
#         self.assertIsNone(dutyswitch.selected_assignment)
#         self.assertEqual(dutyswitch.status, 0)
#
#     def test__selected_was_rejected(self):
#         dutyswitch = DutySwitch.objects.create(
#             source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
#         dutyswitch.selected_was_rejected()
#         self.assertIsNone(dutyswitch.selected_assignment)
#         self.assertEqual(dutyswitch.status, 2)
#
#     def test__look_for_destinations(self):
#         # The reason cleaner1 can't switch with cleaner2 on cleaning_day2
#         Assignment.objects.create(
#             cleaner=self.cleaner1, schedule=self.schedule, cleaning_day=self.cleaning_day2)
#
#         # The reason cleaner3 can't switch with cleaner1 on cleaning_day1
#         Assignment.objects.create(
#             cleaner=self.cleaner3, schedule=self.schedule, cleaning_day=self.cleaning_day1)
#
#         # The only Assignment that is eligible for switching
#         destination = Assignment.objects.create(
#             cleaner=self.cleaner2, schedule=self.schedule, cleaning_day=self.cleaning_day3)
#
#         duty_switch = DutySwitch.objects.create(source_assignment=self.assignment1)
#
#         with patch.object(timezone, 'now', return_value=datetime.datetime(2010, 1, 1)) as mock_now:
#             duty_switch.look_for_destinations()
#
#         self.assertListEqual(list(duty_switch.destinations.all()), [destination])
