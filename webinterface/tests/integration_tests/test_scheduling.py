from django.test import TestCase
from webinterface.models import *

import logging
import timeit
from unittest.mock import *


logging.disable(logging.DEBUG)


class SchedulingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.config = Config.objects.create(date_due=6)

        cls.start_date = correct_dates_to_due_day(datetime.date(2011, 1, 1))
        cls.mid_date = correct_dates_to_due_day(datetime.date(2012, 1, 1))
        cls.end_date = correct_dates_to_due_day(datetime.date(2013, 1, 1))

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
            name="C1", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=1)

        cls.cleaner2 = Cleaner.objects.create(
            name="C2", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=2)

        cls.cleaner3 = Cleaner.objects.create(
            name="C3", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=3)

        cls.cleaner4 = Cleaner.objects.create(
            name="C4", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=1)

        cls.cleaner5 = Cleaner.objects.create(
            name="C5", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c1_to_c5,
            preference=2)

        cls.cleaner6 = Cleaner.objects.create(
            name="C6", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=3)

        cls.cleaner7 = Cleaner.objects.create(
            name="C7", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=1)

        cls.cleaner8 = Cleaner.objects.create(
            name="C8", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=2)

        cls.cleaner9 = Cleaner.objects.create(
            name="C9", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c6_to_c9,
            preference=3)

        cls.cleaner10 = Cleaner.objects.create(
            name="C10", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c10,
            preference=1)

        cls.cleaner11 = Cleaner.objects.create(
            name="C11", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=2)

        cls.cleaner12 = Cleaner.objects.create(
            name="C12", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=3)

        cls.cleaner13 = Cleaner.objects.create(
            name="C13", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=1)

        cls.cleaner14 = Cleaner.objects.create(
            name="C14", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=2)

        cls.cleaner15 = Cleaner.objects.create(
            name="C15", moved_in=cls.start_date, moved_out=cls.end_date, schedule_group=cls.group_c11_to_c15,
            preference=3)

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
            for cleaner in schedule.cleaners_assigned():
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
        for schedule in Schedule.objects.all():
            logging.info("Creating Assignments for {}".format(schedule.name))
            schedule.new_cleaning_duties(self.start_date, self.mid_date)

        print("At middle of time frame: ")
        self.print__cleaning_ratios(self.mid_date)

        # The following cleaners change groups:
        # C2, C3 -> group_c6_to_c9; C7, C8 -> group_c1_to_c5
        #
        self.cleaner2.schedule_group = self.group_c6_to_c9
        self.cleaner3.schedule_group = self.group_c6_to_c9
        self.cleaner7.schedule_group = self.group_c1_to_c5
        self.cleaner8.schedule_group = self.group_c1_to_c5
        self.cleaner2.save()
        self.cleaner3.save()
        self.cleaner7.save()
        self.cleaner8.save()

        for schedule in Schedule.objects.all():
            logging.info("Creating Assignments for {}".format(schedule.name))
            schedule.new_cleaning_duties(self.mid_date, self.end_date)

        print("At end of time frame: ")
        self.print__cleaning_ratios(self.end_date)

        print("Assignments before and after group switching on {}".format(self.mid_date))
        self.print__assignments_in_timeframe(
            self.mid_date-datetime.timedelta(days=60), self.mid_date+datetime.timedelta(days=90))

    def test__no_group_switching__timed(self):
        timing_results = [['All Schedules', 0]]
        start_global = timeit.default_timer()
        for schedule in Schedule.objects.all():
            logging.info("Creating Assignments for {}".format(schedule.name))
            start_schedule = timeit.default_timer()
            schedule.new_cleaning_duties(self.start_date, self.end_date)
            end_schedule = timeit.default_timer()
            timing_results.append([schedule.name, end_schedule - start_schedule])
        end_global = timeit.default_timer()
        timing_results[0][1] = end_global - start_global

        self.print__timing_results(timing_results)
        self.print__assignment_count()
        self.print__cleaning_ratios(self.end_date)




