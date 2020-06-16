from webinterface.models import *
import logging
import sys


# class LogThisTestCase(type):
#     def __new__(cls, name, bases, dct):
#         # if the TestCase already provides setUp, wrap it
#         if 'setUp' in dct:
#             setUp = dct['setUp']
#         else:
#             setUp = lambda self: None
#
#         def wrappedSetUp(self):
#             # for hdlr in self.logger.handlers:
#             #    self.logger.removeHandler(hdlr)
#             self.hdlr = logging.StreamHandler(sys.stdout)
#             self.logger.addHandler(self.hdlr)
#             setUp(self)
#         dct['setUp'] = wrappedSetUp
#
#         # same for tearDown
#         if 'tearDown' in dct:
#             tearDown = dct['tearDown']
#         else:
#             tearDown = lambda self: None
#
#         def wrappedTearDown(self):
#             tearDown(self)
#             self.logger.removeHandler(self.hdlr)
#         dct['tearDown'] = wrappedTearDown
#
#         # return the class instance with the replaced setUp/tearDown
#         return type.__new__(cls, name, bases, dct)


# class BaseFixture(metaclass=LogThisTestCase):
#     logger = logging.getLogger()
#     logger.setLevel(logging.DEBUG)


class BaseFixture:
    @classmethod
    def setUpTestData(cls):
        logging.getLogger('__name__').setLevel(logging.INFO)

        # Config
        cls.start_week = 2500
        cls.mid_week = cls.start_week + 1
        cls.end_week = cls.start_week + 3  # 4 weeks total

        # Schedule
        cls.bathroom_schedule = Schedule.objects.create(name="bathroom", cleaners_per_date=1, weekday=2,
                                                        frequency=1)
        cls.kitchen_schedule = Schedule.objects.create(name="kitchen", cleaners_per_date=2, weekday=4,
                                                       frequency=2)
        cls.bedroom_schedule = Schedule.objects.create(name="bedroom", cleaners_per_date=2, weekday=6,
                                                       frequency=3)
        cls.garage_schedule = Schedule.objects.create(name="garage", cleaners_per_date=1, weekday=0,
                                                      frequency=1, disabled=True)

        # ScheduleGroup
        cls.upper_group = ScheduleGroup.objects.create(name="upper")
        cls.upper_group.schedules.add(cls.bathroom_schedule, cls.kitchen_schedule, cls.bedroom_schedule)

        cls.lower_group = ScheduleGroup.objects.create(name="lower")
        cls.lower_group.schedules.add(cls.kitchen_schedule, cls.bedroom_schedule, cls.garage_schedule)

        # Cleaners
        cls.angie = Cleaner.objects.create(name="angie")
        cls.angie_affiliation = Affiliation.objects.create(
            cleaner=cls.angie, group=cls.upper_group, beginning=cls.start_week, end=cls.end_week
        )

        cls.bob = Cleaner.objects.create(name="bob")
        cls.bob_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.upper_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.bob_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.lower_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.chris = Cleaner.objects.create(name="chris")
        cls.chris_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.lower_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.chris_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.upper_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.dave = Cleaner.objects.create(name="dave")
        cls.dave_affiliation = Affiliation.objects.create(
            cleaner=cls.dave, group=cls.lower_group, beginning=cls.start_week, end=cls.end_week
        )

        # CleaningWeeks
        configuration = {
            2500: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: cls.bob,
                cls.bedroom_schedule: None,  # Bedroom is only defined on odd week numbers
                cls.garage_schedule: cls.dave
            },
            2501: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: None,  # Kitchen is only defined on even week numbers
                cls.bedroom_schedule: cls.chris,
                cls.garage_schedule: cls.dave
            },
            2502: {
                cls.bathroom_schedule: cls.angie,
                cls.kitchen_schedule: cls.chris,
                cls.bedroom_schedule: None,  # Bedroom is only defined on odd week numbers
                cls.garage_schedule: cls.dave
            },
            2503: {
                cls.bathroom_schedule: cls.chris,
                cls.kitchen_schedule: None,  # Kitchen is only defined on even week numbers
                cls.bedroom_schedule: cls.bob,
                cls.garage_schedule: cls.bob
            },
        }

        for week, schedule_and_cleaner in configuration.items():
            for schedule, cleaner in schedule_and_cleaner.items():
                if cleaner is not None:
                    cleaning_week = CleaningWeek.objects.create(week=week, schedule=schedule, assignments_valid=True)
                    setattr(cls, "{}_cleaning_week_{}".format(schedule.name, week),
                            cleaning_week
                            )
                    setattr(cls, "{}_for_{}_in_week_{}".format(cleaner, schedule.name, week),
                            Assignment.objects.create(cleaner=cleaner, schedule=schedule, cleaning_week=cleaning_week)
                            )


class BaseFixtureWithDutySwitch(BaseFixture):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        angie_assignment_2502 = Assignment.objects.get(
            cleaner=cls.angie, schedule=cls.bathroom_schedule,
            cleaning_week=cls.bathroom_schedule.cleaningweek_set.get(week=cls.start_week+2))
        cls.angie_bathroom_dutyswitch_2502 = DutySwitch.objects.create(requester_assignment=angie_assignment_2502)

        dave_assignment_2500 = Assignment.objects.get(
            cleaner=cls.dave, schedule=cls.garage_schedule,
            cleaning_week=cls.garage_schedule.cleaningweek_set.get(week=cls.start_week))
        cls.dave_garage_dutyswitch_2500 = DutySwitch.objects.create(requester_assignment=dave_assignment_2500)

        bob_assignment_2503 = Assignment.objects.get(
            cleaner=cls.bob, schedule=cls.bedroom_schedule,
            cleaning_week=cls.bedroom_schedule.cleaningweek_set.get(week=cls.start_week+3))
        cls.bob_bedroom_dutyswitch_2503 = DutySwitch.objects.create(requester_assignment=bob_assignment_2503)

        bob_assignment_2503_2 = Assignment.objects.get(
            cleaner=cls.bob, schedule=cls.garage_schedule,
            cleaning_week=cls.garage_schedule.cleaningweek_set.get(week=cls.start_week+3))
        cls.bob_garage_dutyswitch_2503 = DutySwitch.objects.create(requester_assignment=bob_assignment_2503_2)

        dave_assignment_2502 = Assignment.objects.get(
            cleaner=cls.dave, schedule=cls.garage_schedule,
            cleaning_week=cls.garage_schedule.cleaningweek_set.get(week=cls.start_week+2))
        bob_assignment_2503 = Assignment.objects.get(
            cleaner=cls.bob, schedule=cls.garage_schedule,
            cleaning_week=cls.garage_schedule.cleaningweek_set.get(week=cls.start_week + 3))
        cls.completed_garage_dutyswitch = DutySwitch.objects.create(requester_assignment=dave_assignment_2502,
                                                                    acceptor_assignment=bob_assignment_2503)


class BaseFixtureWithTasks(BaseFixture):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bathroom_task_template_1 = TaskTemplate.objects.create(name="bathroom_task_1",
                                                                   start_days_before=1, end_days_after=2,
                                                                   schedule=cls.bathroom_schedule)

        cls.bathroom_task_template_2 = TaskTemplate.objects.create(name="bathroom_task_2",
                                                                   start_days_before=3, end_days_after=3,
                                                                   schedule=cls.bathroom_schedule)

        for cleaning_week in CleaningWeek.objects.filter(schedule=cls.bathroom_schedule).all():
            cleaning_week.create_missing_tasks()

        cleaning_week_2500 = CleaningWeek.objects.get(week=cls.start_week, schedule=cls.bathroom_schedule)
        for task in cleaning_week_2500.task_set.all():
            task.cleaned_by = cls.angie
            task.save()
