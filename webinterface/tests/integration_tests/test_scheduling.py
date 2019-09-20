from django.test import TestCase
from webinterface.models import *

import logging
import timeit
from unittest.mock import *


logging.disable(logging.NOTSET)


class SchedulingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.start_date = correct_dates_to_due_day(datetime.date(2011, 6, 1))
        cls.mid_date = correct_dates_to_due_day(datetime.date(2012, 1, 1))
        cls.end_date = correct_dates_to_due_day(datetime.date(2012, 6, 1))

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

        cls.cleaner1 = Cleaner.objects.create(name="C1", preference=1)
        cls.cl1_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner1, group=cls.group_c1_to_c5, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner2 = Cleaner.objects.create(name="C2", preference=2)
        cls.cl2_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner2, group=cls.group_c1_to_c5, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner3 = Cleaner.objects.create(name="C3", preference=3)
        cls.cl3_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner3, group=cls.group_c1_to_c5, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner4 = Cleaner.objects.create(name="C4", preference=1)
        cls.cl4_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner4, group=cls.group_c1_to_c5, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner5 = Cleaner.objects.create(name="C5", preference=2)
        cls.cl5_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner5, group=cls.group_c1_to_c5, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner6 = Cleaner.objects.create(name="C6", preference=3)
        cls.cl6_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner6, group=cls.group_c6_to_c9, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner7 = Cleaner.objects.create(name="C7", preference=1)
        cls.cl7_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner7, group=cls.group_c6_to_c9, beginning=cls.start_date, end=cls.end_date)


        cls.cleaner8 = Cleaner.objects.create(name="C8", preference=2)
        cls.cl8_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner8, group=cls.group_c6_to_c9, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner9 = Cleaner.objects.create(name="C9", preference=3)
        cls.cl9_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner9, group=cls.group_c6_to_c9, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner10 = Cleaner.objects.create(name="C10", preference=1)
        cls.cl10_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner10, group=cls.group_c10, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner11 = Cleaner.objects.create(name="C11", preference=2)
        cls.cl11_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner11, group=cls.group_c11_to_c15, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner12 = Cleaner.objects.create(name="C12", preference=3)
        cls.cl12_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner12, group=cls.group_c11_to_c15, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner13 = Cleaner.objects.create(name="C13", preference=1)
        cls.cl13_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner13, group=cls.group_c11_to_c15, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner14 = Cleaner.objects.create(name="C14", preference=2)
        cls.cl14_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner14, group=cls.group_c11_to_c15, beginning=cls.start_date, end=cls.end_date)

        cls.cleaner15 = Cleaner.objects.create(name="C15", preference=3)
        cls.cl15_affiliation1 = Affiliation.objects.create(
            cleaner=cls.cleaner15, group=cls.group_c11_to_c15, beginning=cls.start_date, end=cls.end_date)

    def print__timing_results(self, timing_results):
        print("")
        print("Timing results")
        for schedule, time in timing_results:
            print("   {}: {}s".format(schedule, round(time, 3)))
        print("")

    def print__assignment_count(self):
        print("Assignment count per Schedule")
        for schedule in Schedule.objects.all():
            print("   Schedule: {}".format(schedule.name))
            for cleaner in Cleaner.objects.filter(affiliation__group__schedules=schedule):
                print("      Cleaner: {} Assignment count: {}".format(
                    cleaner.name, schedule.assignment_set.filter(cleaner=cleaner).count()))
        print("")

    def print__cleaning_ratios(self, date):
        print("Cleaning ratios")
        for schedule in Schedule.objects.all():
            print("   Schedule: {}".format(schedule.name))
            for cleaner, ratio in schedule.deployment_ratios(date):
                print("      Cleaner: {} Ratio: {}".format(cleaner.name, round(ratio, 3)))
        print("")

    def print__assignments_in_timeframe(self, date1, date2):
        print("Schedule assignments")
        for schedule in Schedule.objects.all():
            print("   Schedule: {}".format(schedule.name))
            for cleaning_day in schedule.cleaningday_set.filter(date__range=(min(date1, date2), max(date1, date2))):
                print("      Date: {} Cleaners: ".format(cleaning_day.date), end="")
                for assignment in cleaning_day.assignment_set.all():
                    print(assignment.cleaner, end=" ")
                print("")
        print("")

    def test__switch_groups_at_mid_date(self):
        # for schedule in Schedule.objects.all():
        #     logging.info("Creating Assignments for schedule: {}".format(schedule.name))
        #     schedule.new_cleaning_duties(self.start_date, self.mid_date)
        self.c6_to_c10.new_cleaning_duties(self.start_date, self.mid_date)

        print("At middle of time frame: ")
        self.print__cleaning_ratios(self.mid_date)

        # The following cleaners change groups:
        # C2, C3 -> group_c6_to_c9; C7, C8 -> group_c1_to_c5
        #
        self.cl2_affiliation1.end = self.mid_date
        self.cl2_affiliation1.save()
        self.cl2_affiliation2 = Affiliation.objects.create(
            cleaner=self.cleaner2, group=self.group_c6_to_c9, beginning=self.mid_date, end=self.end_date)

        self.cl3_affiliation1.end = self.mid_date
        self.cl3_affiliation1.save()
        self.cl3_affiliation2 = Affiliation.objects.create(
            cleaner=self.cleaner3, group=self.group_c6_to_c9, beginning=self.mid_date, end=self.end_date)

        self.cl7_affiliation1.end = self.mid_date
        self.cl7_affiliation1.save()
        self.cl7_affiliation2 = Affiliation.objects.create(
            cleaner=self.cleaner7, group=self.group_c1_to_c5, beginning=self.mid_date, end=self.end_date)

        self.cl8_affiliation1.end = self.mid_date
        self.cl8_affiliation1.save()
        self.cl8_affiliation2 = Affiliation.objects.create(
            cleaner=self.cleaner8, group=self.group_c1_to_c5, beginning=self.mid_date, end=self.end_date)

        # for schedule in Schedule.objects.all():
        #     logging.info("Creating Assignments for {}".format(schedule.name))
        #     schedule.new_cleaning_duties(self.mid_date, self.end_date)
        self.c6_to_c10.new_cleaning_duties(self.mid_date, self.end_date)

        print("At end of time frame: ")
        self.print__cleaning_ratios(self.end_date)

        print("Assignments before and after group switching on {}".format(self.mid_date))
        print("The following cleaners have changed groups: C2, C3 -> group_c6_to_c9; C7, C8 -> group_c1_to_c5")
        self.print__assignments_in_timeframe(
            self.mid_date-datetime.timedelta(days=60), self.mid_date+datetime.timedelta(days=90))

    def test__no_group_switching__timed(self):
        timing_results = [['All Schedules', 0]]
        start_global = timeit.default_timer()
        for schedule in Schedule.objects.all():
            logging.info("Creating Assignments for schedule: {}".format(schedule.name))
            start_schedule = timeit.default_timer()
            schedule.new_cleaning_duties(self.start_date, self.end_date)
            end_schedule = timeit.default_timer()
            timing_results.append([schedule.name, end_schedule - start_schedule])
        end_global = timeit.default_timer()
        timing_results[0][1] = end_global - start_global

        self.print__timing_results(timing_results)
        self.print__assignment_count()
        self.print__cleaning_ratios(self.end_date)




