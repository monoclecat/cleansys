from django.test import TestCase
from webinterface.models import *

import logging
import timeit
from unittest.mock import *


#logging.disable(logging.DEBUG)


class SchedulingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6)

        cls.start_date = correct_dates_to_due_day(datetime.date(2011, 1, 1))
        cls.end_date = correct_dates_to_due_day(datetime.date(2011, 7, 1))

        # The names indicate which cleaners are assigned
        cls.all = Schedule.objects.create(name="all", cleaners_per_date=2, frequency=1)  # Bar
        cls.all_even_weeks = Schedule.objects.create(name="all_even_weeks", cleaners_per_date=2, frequency=2)  # Holztreppe
        cls.all_odd_weeks = Schedule.objects.create(name="all_odd_weeks", cleaners_per_date=2, frequency=3)  # Marmortreppe
        cls.c1_to_c9 = Schedule.objects.create(name="c1_to_c9", cleaners_per_date=2, frequency=1)  # EG Küche
        cls.c10_to_c15 = Schedule.objects.create(name="c10_to_c15", cleaners_per_date=2, frequency=1)  # 3.OG Küche
        cls.c1_to_c5 = Schedule.objects.create(name="c1_to_c5", cleaners_per_date=1, frequency=1)  # Bad EG
        cls.c6_to_c10 = Schedule.objects.create(name="c6_to_c10", cleaners_per_date=1, frequency=1)  # Bad 2.OG
        cls.c11_to_c15 = Schedule.objects.create(name="c11_to_c15", cleaners_per_date=1, frequency=1)  # Bad 3.OG

        cls.group_c1_to_c5 = ScheduleGroup.objects.create(name="group_c1_to_c5")  # EG
        cls.group_c6_to_c9 = ScheduleGroup.objects.create(name="group_c6_to_c9")  # 2.OG - EG Küche
        cls.group_c10 = ScheduleGroup.objects.create(name="group_c10")  # 2.OG - 3.OG Küche
        cls.group_c11_to_c15 = ScheduleGroup.objects.create(name="group_c11_to_c15")  # 3.OG

        cls.group_c1_to_c5.schedules.add(
            cls.c1_to_c5, cls.c1_to_c9, cls.all, cls.all_even_weeks, cls.all_odd_weeks)

        cls.group_c6_to_c9.schedules.add(
            cls.c6_to_c10, cls.c1_to_c9, cls.all, cls.all_even_weeks, cls.all_odd_weeks)

        cls.group_c10.schedules.add(
            cls.c6_to_c10, cls.c10_to_c15, cls.all, cls.all_even_weeks, cls.all_odd_weeks)

        cls.group_c11_to_c15.schedules.add(
            cls.c11_to_c15, cls.c10_to_c15, cls.all, cls.all_even_weeks, cls.all_odd_weeks)


        cls.cleaner1 = Cleaner.objects.create(
            name="C1_pref=1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=1)

        cls.cleaner2 = Cleaner.objects.create(
            name="C2_pref=2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=2)

        cls.cleaner3 = Cleaner.objects.create(
            name="C3_pref=3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=3)

        cls.cleaner4 = Cleaner.objects.create(
            name="C4_pref=1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=1)

        cls.cleaner5 = Cleaner.objects.create(
            name="C5_pref=2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=2)

        cls.cleaner6 = Cleaner.objects.create(
            name="C6_pref=3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=3)

        cls.cleaner7 = Cleaner.objects.create(
            name="C7_pref=1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=1)

        cls.cleaner8 = Cleaner.objects.create(
            name="C8_pref=2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=2)

        cls.cleaner9 = Cleaner.objects.create(
            name="C9_pref=3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=3)

        cls.cleaner10 = Cleaner.objects.create(
            name="C10_pref=1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c10,
            preference=1)

        cls.cleaner11 = Cleaner.objects.create(
            name="C11_pref=2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=2)

        cls.cleaner12 = Cleaner.objects.create(
            name="C12_pref=3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=3)

        cls.cleaner13 = Cleaner.objects.create(
            name="C13_pref=1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=1)

        cls.cleaner14 = Cleaner.objects.create(
            name="C14_pref=2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=2)

        cls.cleaner15 = Cleaner.objects.create(
            name="C15_pref=3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=3)

        cls.timing_results = [['All Schedules', 0]]
        start_global = timeit.default_timer()
        for schedule in Schedule.objects.all():
            logging.info("Creating Assignments for {}".format(schedule.name))
            start_schedule = timeit.default_timer()
            schedule.new_cleaning_duties(cls.start_date, cls.end_date)
            end_schedule = timeit.default_timer()
            cls.timing_results.append([schedule.name, end_schedule - start_schedule])
        end_global = timeit.default_timer()
        cls.timing_results[0][1] = end_global - start_global

    def test_output_timing_results(self):
        print("")
        print("Timing results")
        for schedule, time in self.timing_results:
            print("   {}: {}s".format(schedule, round(time, 3)))
        print("")

    def test_output_assignment_count(self):
        print("")
        print("Assignment count per Schedule")
        for schedule in Schedule.objects.all():
            print("   Schedule: {}".format(schedule.name))
            for cleaner in schedule.cleaners_assigned():
                print("      Cleaner: {} Assignment count: {}".format(
                    cleaner.name, schedule.assignment_set.filter(cleaner=cleaner).count()))
        print("")

    def test_output_ratios(self):
        print("")
        print("Cleaning ratios")
        for schedule in Schedule.objects.all():
            print("   Schedule: {}".format(schedule.name))
            for cleaner, ratio in schedule.deployment_ratios(self.end_date):
                print("      Cleaner: {} Ratio: {}".format(cleaner.name, round(ratio, 3)))
        print("")
