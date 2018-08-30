from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

logging.disable(logging.FATAL)


class HelperFunctionsTest(TestCase):
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
        self.assertEqual(correct_dates_to_due_day(reference_date).weekday(), 6)

        corrected_list = correct_dates_to_weekday([reference_date, reference_date], 6)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 6)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 6))


class ScheduleTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_datetime = datetime.datetime(2010, 1, 8)
        cls.reference_date = correct_dates_to_due_day(cls.reference_datetime.date())
        cls.one_week = timezone.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=3)
        cls.no_assignment_schedule = Schedule.objects.create(name="no_assignment_sch", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule, cls.no_assignment_schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=1)
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_day1 = CleaningDay.objects.create(
            date=correct_dates_to_due_day(cls.reference_date), schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=correct_dates_to_due_day(
            cls.reference_date + cls.one_week), schedule=cls.schedule)
        cls.cleaning_day3 = CleaningDay.objects.create(date=correct_dates_to_due_day(
            cls.reference_date + 2 * cls.one_week), schedule=cls.schedule)

        # Affiliations
        cls.cleaner1_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.reference_date,
            end=cls.reference_date + 3 * cls.one_week)
        cls.cleaner2_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner2, group=cls.group, beginning=cls.reference_date,
            end=cls.reference_date + 3 * cls.one_week)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment4 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)

        # DutySwitch Requests
        cls.rejected_dutyswitch = DutySwitch.objects.create(status=2, source_assignment=cls.assignment1)
        cls.dutyswitch_request_received = DutySwitch.objects.create(source_assignment=cls.assignment2,
                                                                    selected_assignment=cls.assignment1)
        cls.pending_dutyswitch_request = DutySwitch.objects.create(status=1, source_assignment=cls.assignment1)

    def test__creation(self):
        schedule = Schedule.objects.create()
        self.assertIsInstance(schedule, Schedule)
        self.assertEqual(schedule.slug, slugify(schedule.name))

    def test__str(self):
        self.assertEqual(self.schedule.__str__(), self.schedule.name)

    def test__deployment_ratios__no_cleaners(self):
        schedule = Schedule()
        self.assertListEqual(schedule.deployment_ratios(self.reference_date), [])

    def test__deployment_ratios__cleaners_have_no_assignments(self):
        container = self.no_assignment_schedule.deployment_ratios(self.reference_date)

        self.assertIn([self.cleaner1, 0], container)
        self.assertIn([self.cleaner2, 0], container)
        self.assertEqual(len(container), 2)

    def test__deployment_ratios(self):
        ratios = self.schedule.deployment_ratios(self.cleaning_day1.date)
        self.assertIn([self.cleaner1, 1/4], ratios)
        self.assertIn([self.cleaner2, 3/4], ratios)
        self.assertEqual(len(ratios), 2)

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
        date1, date2 = [self.reference_date, self.reference_date + 4 * self.one_week]

        with patch.object(Schedule, 'create_assignment', return_value=False) as mock_create_assignment:
            self.schedule.new_cleaning_duties(date2, date1, 2)
            new_assignment_set = self.schedule.assignment_set.all()
            self.assertIn(self.assignment1, new_assignment_set)
            self.assertIn(self.assignment2, new_assignment_set)
            self.assertIn(self.assignment3, new_assignment_set)
            self.assertIn(self.assignment4, new_assignment_set)

            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(date1), call(date1 + self.one_week), call(date1 + 2 * self.one_week),
                                  call(date1 + 3 * self.one_week), call(date1 + 4 * self.one_week)])

    def test__new_cleaning_duties__clear_existing_assignments(self):
        date1, date2 = [self.reference_date, self.reference_date + 4 * self.one_week]

        with patch.object(Schedule, 'create_assignment', return_value=False) as mock_create_assignment:
            self.schedule.new_cleaning_duties(date2, date1, 1)
            new_assignment_set = self.schedule.assignment_set.all()
            self.assertNotIn(self.assignment1, new_assignment_set)
            self.assertNotIn(self.assignment2, new_assignment_set)
            self.assertNotIn(self.assignment3, new_assignment_set)
            self.assertNotIn(self.assignment4, new_assignment_set)
            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(date1), call(date1 + self.one_week), call(date1 + 2 * self.one_week),
                                  call(date1 + 3 * self.one_week), call(date1 + 4 * self.one_week)])

    def test__new_cleaning_duties__only_reassign_existing(self):
        date1, date2 = [self.reference_date, self.reference_date + 4 * self.one_week]

        with patch.object(Schedule, 'create_assignment', return_value=False) as mock_create_assignment:
            self.schedule.new_cleaning_duties(date2, date1, 3)
            new_assignment_set = self.schedule.assignment_set.all()
            self.assertNotIn(self.assignment1, new_assignment_set)
            self.assertNotIn(self.assignment2, new_assignment_set)
            self.assertNotIn(self.assignment3, new_assignment_set)
            self.assertNotIn(self.assignment4, new_assignment_set)
            self.assertListEqual(mock_create_assignment.mock_calls,
                                 [call(date1), call(date1 + self.one_week)])

    def test__create_assignment__not_defined_on_date(self):
        even_week_schedule = Schedule(frequency=2)
        odd_week = datetime.date(2010, 2, 15)
        self.assertFalse(even_week_schedule.create_assignment(odd_week))

    def test__create_assignment__no_ratios(self):
        day = datetime.date(2010, 2, 15)
        no_group_schedule = Schedule.objects.create(name="no_group_schedule", cleaners_per_date=1, frequency=1)
        self.assertFalse(no_group_schedule.create_assignment(day))

    def test__create_assignment__no_eligible_cleaner(self):
        assignment = self.schedule.create_assignment(self.cleaning_day1.date)
        self.assertEqual(assignment.cleaner, self.schedule.deployment_ratios(self.cleaning_day1.date)[0][0])

    def test__create_assignment__all_cleaners_excluded(self):
        self.cleaning_day1.excluded.add(self.cleaner1, self.cleaner2)
        assignment = self.schedule.create_assignment(self.cleaning_day1.date)
        self.assertEqual(assignment.cleaner, self.schedule.deployment_ratios(self.cleaning_day1.date)[0][0])

    def test__create_assignment__eligible_cleaners(self):
        assignment = self.schedule.create_assignment(self.cleaning_day2.date)
        self.assertEqual(assignment.cleaner, self.cleaner1)
        self.assertEqual(assignment.cleaning_day, self.cleaning_day2)


class ScheduleGroupTest(TestCase):
    def test__creation(self):
        group = ScheduleGroup.objects.create()
        self.assertIsInstance(group, ScheduleGroup)

    def test__str(self):
        group = ScheduleGroup(name="test")
        self.assertEqual(group.__str__(), group.name)


class CleanerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_datetime = datetime.datetime(2010, 1, 8)
        cls.reference_date = correct_dates_to_due_day(cls.reference_datetime.date())
        cls.one_week = timezone.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=2)
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_day1 = CleaningDay.objects.create(
            date=correct_dates_to_due_day(cls.reference_date), schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=correct_dates_to_due_day(
            cls.reference_date + cls.one_week), schedule=cls.schedule)
        cls.cleaning_day3 = CleaningDay.objects.create(date=correct_dates_to_due_day(
            cls.reference_date - cls.one_week), schedule=cls.schedule)

        # Affiliations
        cls.cleaner1_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.reference_date, end=cls.reference_date+2*cls.one_week)
        cls.cleaner2_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner2, group=cls.group, beginning=cls.reference_date, end=cls.reference_date+2*cls.one_week)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment4 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment_outside_of_affiliation = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day3)

        # DutySwitch Requests
        cls.rejected_dutyswitch = DutySwitch.objects.create(status=2, source_assignment=cls.assignment1)
        cls.dutyswitch_request_received = DutySwitch.objects.create(source_assignment=cls.assignment2,
                                                                    selected_assignment=cls.assignment1)
        cls.pending_dutyswitch_request = DutySwitch.objects.create(status=1, source_assignment=cls.assignment1)

    def test__creation(self):
        cleaner = Cleaner.objects.create(name="bob")
        self.assertIsInstance(cleaner, Cleaner)
        self.assertEqual(cleaner.slug, slugify(cleaner.name))

    def test__str(self):
        cleaner = Cleaner(name="bob")
        self.assertEqual(cleaner.__str__(), cleaner.name)

    def test__current_affiliation__exists(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime + self.one_week) as mock_now:
            self.assertEqual(self.cleaner1.current_affiliation(), self.cleaner1_affiliation)

    def test__current_affiliation__none(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime - self.one_week) as mock_now:
            self.assertIsNone(self.cleaner1.current_affiliation())

    def test__all_assignments_during_affiliation_with_schedule(self):
        all_assignments = self.cleaner1.all_assignments_during_affiliation_with_schedule(self.schedule)

        self.assertIn(self.assignment1, all_assignments)
        self.assertIn(self.assignment2, all_assignments)
        self.assertIn(self.assignment3, all_assignments)
        self.assertIn(self.assignment4, all_assignments)
        self.assertNotIn(self.assignment_outside_of_affiliation, all_assignments)

    def test__own_assignments_during_affiliation_with_schedule(self):
        assignments_cleaner1 = self.cleaner1.own_assignments_during_affiliation_with_schedule(self.schedule)
        assignments_cleaner2 = self.cleaner2.own_assignments_during_affiliation_with_schedule(self.schedule)

        self.assertIn(self.assignment1, assignments_cleaner1)
        self.assertNotIn(self.assignment2, assignments_cleaner1)
        self.assertNotIn(self.assignment3, assignments_cleaner1)
        self.assertNotIn(self.assignment4, assignments_cleaner1)
        self.assertNotIn(self.assignment_outside_of_affiliation, assignments_cleaner1)

        self.assertNotIn(self.assignment1, assignments_cleaner2)
        self.assertIn(self.assignment2, assignments_cleaner2)
        self.assertIn(self.assignment3, assignments_cleaner2)
        self.assertIn(self.assignment4, assignments_cleaner2)
        self.assertNotIn(self.assignment_outside_of_affiliation, assignments_cleaner2)

    def test__deployment_ratio_for_schedule(self):
        cleaner1_ratio = self.cleaner1.deployment_ratio_for_schedule(self.schedule)
        cleaner2_ratio = self.cleaner2.deployment_ratio_for_schedule(self.schedule)

        self.assertEqual(cleaner1_ratio, 1/4)
        self.assertEqual(cleaner2_ratio, 3/4)

    def test__is_active(self):
        with patch.object(timezone, 'now', return_value=self.reference_datetime + self.one_week) as mock_now:
            self.assertTrue(self.cleaner1.is_active())
        with patch.object(timezone, 'now', return_value=self.reference_datetime - self.one_week) as mock_now:
            self.assertFalse(self.cleaner1.is_active())

    def test__rejected_dutyswitch_requests(self):
        rejected_dutyswitch_requests = self.cleaner1.rejected_dutyswitch_requests()
        self.assertIn(self.rejected_dutyswitch, rejected_dutyswitch_requests)
        self.assertNotIn(self.dutyswitch_request_received, rejected_dutyswitch_requests)
        self.assertNotIn(self.pending_dutyswitch_request, rejected_dutyswitch_requests)

    def test__dutyswitch_requests_received(self):
        dutyswitch_requests_received = self.cleaner1.dutyswitch_requests_received()
        self.assertNotIn(self.rejected_dutyswitch, dutyswitch_requests_received)
        self.assertIn(self.dutyswitch_request_received, dutyswitch_requests_received)
        self.assertNotIn(self.pending_dutyswitch_request, dutyswitch_requests_received)

    def test__pending_dutyswitch_requests(self):
        pending_dutyswitch_requests = self.cleaner1.pending_dutyswitch_requests()
        self.assertNotIn(self.rejected_dutyswitch, pending_dutyswitch_requests)
        self.assertNotIn(self.dutyswitch_request_received, pending_dutyswitch_requests)
        self.assertIn(self.pending_dutyswitch_request, pending_dutyswitch_requests)

    def test__has_pending_requests(self):
        self.assertTrue(self.cleaner1.has_pending_requests())
        self.assertFalse(self.cleaner3.has_pending_requests())

    def test__nr_assignments_on_day(self):
        self.assertEqual(self.cleaner1.nr_assignments_on_day(self.cleaning_day1.date), 1)
        self.assertEqual(self.cleaner1.nr_assignments_on_day(self.cleaning_day2.date), 0)

    def test__is_eligible_for_date(self):
        self.assertFalse(self.cleaner1.is_eligible_for_date(self.cleaning_day1.date))
        self.assertTrue(self.cleaner1.is_eligible_for_date(self.cleaning_day2.date))

        self.assertTrue(self.cleaner2.is_eligible_for_date(self.cleaning_day1.date))
        self.assertFalse(self.cleaner2.is_eligible_for_date(self.cleaning_day2.date))

    def test__delete(self):
        cleaner_to_delete = Cleaner.objects.create(name="cleaner_to_delete")
        user_to_delete = cleaner_to_delete.user
        cleaner_to_delete.delete()
        self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())

    def test__save__slug_changes(self):
        cleaner = Cleaner.objects.create(name="cleaner_original_slug")
        cleaner.name = "cleaner_new_slug"
        with patch.object(User, "set_password") as mock_user_set_pw:
            cleaner.save()
            self.assertEqual(cleaner.user.username, cleaner.slug)
            self.assertListEqual(mock_user_set_pw.mock_calls, [call(cleaner.slug)])

    def test__save__new_slug(self):
        cleaner = Cleaner.objects.create(name="new_cleaner")
        self.assertTrue(User.objects.filter(username=cleaner.slug).exists())
        user = User.objects.get(username=cleaner.slug)
        self.assertTrue(User.objects.filter(username=cleaner.slug).first().check_password(cleaner.slug))


class AffiliationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.beginning_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.one_week = timezone.timedelta(days=7)
        cls.end_date = cls.beginning_date + 4*cls.one_week

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)

        # Affiliation
        cls.prev_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.beginning_date-4*cls.one_week, end=cls.beginning_date)
        cls.affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.beginning_date, end=cls.end_date)
        cls.next_affiliation = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.end_date, end=cls.end_date+4*cls.one_week)

    def test__creation(self):
        affiliation = Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                                 beginning=datetime.date(2011, 1, 1))
        self.assertIsInstance(affiliation, Affiliation)

    def test__str(self):
        affiliation = Affiliation(cleaner=self.cleaner1, group=self.group, beginning=self.beginning_date,
                                  end=self.end_date)
        affil_str = str(affiliation)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.beginning_date), affil_str)
        self.assertIn(str(self.end_date), affil_str)

    def test__str__no_end(self):
        affiliation_no_end = Affiliation(cleaner=self.cleaner1, group=self.group, beginning=self.beginning_date)
        affil_str = str(affiliation_no_end)
        self.assertIn(self.cleaner1.name, affil_str)
        self.assertIn(self.group.name, affil_str)
        self.assertIn(str(self.beginning_date), affil_str)

    def test__delete(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            affiliation = Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                                     beginning=datetime.date(2011, 1, 1), end=datetime.date(2011, 2, 1))
            affiliation.delete()
            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(datetime.date(2011, 1, 1), datetime.date(2011, 2, 1), 3)])

    def test__save__end_before_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.end = affiliation.beginning - self.one_week
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__group_change(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.group = ScheduleGroup(name="temp")
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__cleaner_change(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.cleaner = Cleaner(name="temp")
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__set_beginning_before_other_beginning(self):
        affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
        affiliation.beginning = self.prev_affiliation.beginning - self.one_week
        with self.assertRaises(OperationalError):
            affiliation.save()

    def test__save__create_with_beginning_before_other_beginning(self):
        with self.assertRaises(OperationalError):
            Affiliation.objects.create(cleaner=self.cleaner1, group=self.group,
                                       beginning=self.next_affiliation.beginning - self.one_week)

    def test__save__beginning_changes(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            __prev_affiliation_dates = [self.prev_affiliation.beginning, self.prev_affiliation.end]
            __next_affiliation_dates = [self.next_affiliation.beginning, self.next_affiliation.end]

            affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
            affiliation.beginning = affiliation.beginning-self.one_week
            affiliation.save()

            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(self.beginning_date - self.one_week, self.beginning_date, 3)])

            prev_affiliation = Affiliation.objects.get(pk=self.prev_affiliation.pk)
            self.assertEqual(__prev_affiliation_dates,
                             [prev_affiliation.beginning, prev_affiliation.end+self.one_week])

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            self.assertEqual(__next_affiliation_dates, [next_affiliation.beginning, next_affiliation.end])

    def test__save__end_changes(self):
        with patch.object(Schedule, "new_cleaning_duties") as mock_new_cleaning_duties:
            __prev_affiliation_dates = [self.prev_affiliation.beginning, self.prev_affiliation.end]

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            next_affiliation.beginning = next_affiliation.beginning + self.one_week
            next_affiliation.save()
            __next_affiliation_dates = [next_affiliation.beginning, next_affiliation.end]
            mock_new_cleaning_duties.mock_calls = []

            affiliation = Affiliation.objects.get(pk=self.affiliation.pk)
            affiliation.end = affiliation.end+self.one_week
            affiliation.save()

            self.assertEqual(mock_new_cleaning_duties.mock_calls,
                             [call(self.end_date, self.end_date+self.one_week, 3)])

            prev_affiliation = Affiliation.objects.get(pk=self.prev_affiliation.pk)
            self.assertEqual(__prev_affiliation_dates, [prev_affiliation.beginning, prev_affiliation.end])

            next_affiliation = Affiliation.objects.get(pk=self.next_affiliation.pk)
            self.assertEqual(__next_affiliation_dates, [next_affiliation.beginning, next_affiliation.end])


class CleaningDayTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.cleaning_day = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.task1 = Task.objects.create(name="task1", schedule=cls.schedule, start_weekday=4, end_weekday=2)
        cls.task2 = Task.objects.create(name="task2", schedule=cls.schedule)
        cls.cleaner = Cleaner.objects.create(name="cleaner")
        cls.assignment = Assignment.objects.create(
            cleaner=cls.cleaner, schedule=cls.schedule, cleaning_day=cls.cleaning_day)
        cls.assignment.tasks_cleaned.add(cls.task1)

    def test__creation(self):
        cleaning_day = CleaningDay.objects.create(date=datetime.date(2010, 2, 8), schedule=self.schedule)
        self.assertIsInstance(cleaning_day, CleaningDay)

    def test__str(self):
        self.assertIn(self.schedule.name, self.cleaning_day.__str__())
        self.assertIn(self.cleaning_day.date.strftime('%d-%b-%Y'), self.cleaning_day.__str__())

    def test__cleaning_start_date(self):
        self.assertEqual(self.cleaning_day.cleaning_start_date(),
                         self.reference_date - datetime.timedelta(days=6-self.task1.start_weekday))

    def test__cleaning_end_date(self):
        self.assertEqual(self.cleaning_day.cleaning_end_date(),
                         self.reference_date - datetime.timedelta(days=1 + self.task1.end_weekday))

    def test__task_list(self):
        with patch.object(timezone, 'now') as mock_now:
            mock_date = Mock()
            mock_date.date.return_value = self.reference_date - datetime.timedelta(days=2)
            mock_now.return_value = mock_date
            task_list = self.cleaning_day.task_list()
            self.assertIn([self.task1, self.assignment, True], task_list)
            self.assertIn([self.task2, None, False], task_list)


class TaskQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.enabled_task = Task.objects.create(name="enabledtask", disabled=False, schedule=cls.schedule)
        cls.disabled_task = Task.objects.create(name="disabledtask", disabled=True, schedule=cls.schedule)

    def test__enabled(self):
        enabled_queryset = Task.objects.enabled()
        self.assertIn(self.enabled_task, enabled_queryset)
        self.assertNotIn(self.disabled_task, enabled_queryset)

    def test__disabled(self):
        disabled_queryset = Task.objects.disabled()
        self.assertNotIn(self.enabled_task, disabled_queryset)
        self.assertIn(self.disabled_task, disabled_queryset)


class TaskTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.schedule = Schedule.objects.create(name="schedule")
        cls.cleaning_day = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)

    def test__creation(self):
        task = Task.objects.create(name="task1", schedule=self.schedule)
        self.assertIsInstance(task, Task)

    def test__str(self):
        task = Task(name="task1")
        self.assertEqual(task.name, task.__str__())


class AssignmentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        one_week = timezone.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1")
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2")
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3")

        # CleaningDays
        cls.cleaning_day1 = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=cls.reference_date + one_week, schedule=cls.schedule)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)

        # DutySwitch
        cls.dutyswitch = DutySwitch.objects.create(source_assignment=cls.assignment1)

    def test__creation(self):
        assignment = Assignment.objects.create(cleaner=self.cleaner1, schedule=self.schedule,
                                               cleaning_day=self.cleaning_day1)
        self.assertIsInstance(assignment, Assignment)

    def test__str(self):
        self.assertIn(self.schedule.name, self.assignment1.__str__())
        self.assertIn(self.cleaner1.name, self.assignment1.__str__())
        self.assertIn(self.assignment1.cleaning_day.date.strftime('%d-%b-%Y'), self.assignment1.__str__())

    def test__cleaners_on_day_for_schedule(self):
        cleaners_on_date_for_schedule = self.assignment1.cleaners_on_date_for_schedule()
        self.assertIn(self.cleaner1, cleaners_on_date_for_schedule)
        self.assertIn(self.cleaner2, cleaners_on_date_for_schedule)
        self.assertNotIn(self.cleaner3, cleaners_on_date_for_schedule)

    def test__cleaning_buddies(self):
        cleaners_on_date_for_schedule = self.assignment1.cleaning_buddies()
        self.assertNotIn(self.cleaner1, cleaners_on_date_for_schedule)
        self.assertIn(self.cleaner2, cleaners_on_date_for_schedule)
        self.assertNotIn(self.cleaner3, cleaners_on_date_for_schedule)

    def test__is_source_of_dutyswitch(self):
        self.assertEqual(self.assignment1.is_source_of_dutyswitch(), self.dutyswitch)
        self.assertEqual(self.assignment2.is_source_of_dutyswitch(), None)


class DutySwitchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Config
        cls.reference_date = correct_dates_to_due_day(datetime.date(2010, 1, 8))
        cls.one_week = datetime.timedelta(days=7)

        # Schedule
        cls.schedule = Schedule.objects.create(name="schedule", cleaners_per_date=2, frequency=2)

        # ScheduleGroup
        cls.group = ScheduleGroup.objects.create(name="group")
        cls.group.schedules.add(cls.schedule)

        # Cleaners
        cls.cleaner1 = Cleaner.objects.create(name="cleaner1", preference=1)
        cls.cleaner2 = Cleaner.objects.create(name="cleaner2", preference=1)
        cls.cleaner3 = Cleaner.objects.create(name="cleaner3", preference=1)

        # Affiliations
        cls.cl1_affil = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group, beginning=cls.reference_date,
            end=cls.reference_date + 4 * cls.one_week)
        cls.cl2_affil = Affiliation.objects.create(
            cleaner=cls.cleaner2, group=cls.group, beginning=cls.reference_date,
            end=cls.reference_date + 4 * cls.one_week)
        cls.cl3_affil = Affiliation.objects.create(
            cleaner=cls.cleaner3, group=cls.group, beginning=cls.reference_date,
            end=cls.reference_date + 4 * cls.one_week)

        # CleaningDays
        cls.cleaning_day1 = CleaningDay.objects.create(date=cls.reference_date, schedule=cls.schedule)
        cls.cleaning_day2 = CleaningDay.objects.create(date=cls.reference_date + cls.one_week, schedule=cls.schedule)
        cls.cleaning_day3 = CleaningDay.objects.create(
            date=cls.reference_date + 2 * cls.one_week, schedule=cls.schedule)

        # Assignments
        cls.assignment1 = Assignment.objects.create(
            cleaner=cls.cleaner1, schedule=cls.schedule, cleaning_day=cls.cleaning_day1)
        cls.assignment2 = Assignment.objects.create(
            cleaner=cls.cleaner2, schedule=cls.schedule, cleaning_day=cls.cleaning_day2)
        cls.assignment3 = Assignment.objects.create(
            cleaner=cls.cleaner3, schedule=cls.schedule, cleaning_day=cls.cleaning_day3)

        # DutySwitch requests
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

    def test__destinations_without_source_and_selected(self):
        self.switch_1_with_2.destinations.add(self.assignment1, self.assignment2, self.assignment3)
        destinations = self.switch_1_with_2.destinations_without_source_and_selected()
        self.assertNotIn(self.assignment1, destinations)
        self.assertNotIn(self.assignment2, destinations)
        self.assertIn(self.assignment3, destinations)

    def test__set_selected(self):
        self.switch_1.set_selected(self.assignment2)
        self.assertEqual(self.switch_1.selected_assignment, self.assignment2)
        self.assertEqual(self.switch_1.status, 1)

    def test__selected_was_accepted(self):
        # On these the function selected_was_rejected() will be called
        assignment1__is__selected_assignment = DutySwitch.objects.create(
            source_assignment=self.assignment3, selected_assignment=self.assignment1, status=1)
        assignment2__is__selected_assignment = DutySwitch.objects.create(
            source_assignment=self.assignment3, selected_assignment=self.assignment2, status=1)

        # These will be deleted
        assignment1__is__source_assignment = DutySwitch.objects.create(source_assignment=self.assignment1, status=0)
        assignment2__is__source_assignment = DutySwitch.objects.create(source_assignment=self.assignment2, status=0)

        old_assignment_1_date = self.assignment1.cleaning_day.date
        old_assignment_2_date = self.assignment2.cleaning_day.date

        dutyswitch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
        dutyswitch.selected_was_accepted()

        self.assertIn(self.assignment1.cleaner, self.cleaning_day1.excluded.all())
        self.assertNotIn(self.assignment2.cleaner, self.cleaning_day1.excluded.all())

        self.assertEqual(self.assignment1.cleaning_day.date, old_assignment_2_date)
        self.assertEqual(self.assignment2.cleaning_day.date, old_assignment_1_date)

        self.assertEqual(DutySwitch.objects.get(pk=assignment1__is__selected_assignment.pk).status, 2)
        self.assertEqual(DutySwitch.objects.get(pk=assignment2__is__selected_assignment.pk).status, 2)

        self.assertFalse(DutySwitch.objects.filter(pk=assignment1__is__source_assignment.pk).exists())
        self.assertFalse(DutySwitch.objects.filter(pk=assignment2__is__source_assignment.pk).exists())
        self.assertFalse(DutySwitch.objects.filter(pk=self.switch_1_with_2.pk).exists())

    def test__selected_was_cancelled(self):
        dutyswitch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
        dutyswitch.selected_was_cancelled()
        self.assertIsNone(dutyswitch.selected_assignment)
        self.assertEqual(dutyswitch.status, 0)

    def test__selected_was_rejected(self):
        dutyswitch = DutySwitch.objects.create(
            source_assignment=self.assignment1, selected_assignment=self.assignment2, status=1)
        dutyswitch.selected_was_rejected()
        self.assertIsNone(dutyswitch.selected_assignment)
        self.assertEqual(dutyswitch.status, 2)

    def test__look_for_destinations(self):
        # The reason cleaner1 can't switch with cleaner2 on cleaning_day2
        Assignment.objects.create(
            cleaner=self.cleaner1, schedule=self.schedule, cleaning_day=self.cleaning_day2)

        # The reason cleaner3 can't switch with cleaner1 on cleaning_day1
        Assignment.objects.create(
            cleaner=self.cleaner3, schedule=self.schedule, cleaning_day=self.cleaning_day1)

        # The only Assignment that is eligible for switching
        destination = Assignment.objects.create(
            cleaner=self.cleaner2, schedule=self.schedule, cleaning_day=self.cleaning_day3)

        duty_switch = DutySwitch.objects.create(source_assignment=self.assignment1)

        with patch.object(timezone, 'now', return_value=datetime.datetime(2010, 1, 1)) as mock_now:
            duty_switch.look_for_destinations()

        self.assertListEqual(list(duty_switch.destinations.all()), [destination])

