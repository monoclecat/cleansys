from webinterface.models import *


class BaseFixture:
    @classmethod
    def setUpTestData(cls):
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
        cls.angie = Cleaner.objects.create(name="angie", preference=1)  # Max one duty a week please
        cls.angie_affiliation = Affiliation.objects.create(
            cleaner=cls.angie, group=cls.upper_group, beginning=cls.start_week, end=cls.end_week
        )

        cls.bob = Cleaner.objects.create(name="bob", preference=2)  # Max two duties a week please
        cls.bob_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.upper_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.bob_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.bob, group=cls.lower_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.chris = Cleaner.objects.create(name="chris", preference=3)  # I don't care how many duties a week
        cls.chris_affiliation_1 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.lower_group, beginning=cls.start_week, end=cls.mid_week
        )
        cls.chris_affiliation_2 = Affiliation.objects.create(
            cleaner=cls.chris, group=cls.upper_group, beginning=cls.mid_week+1, end=cls.end_week
        )

        cls.dave = Cleaner.objects.create(name="dave", preference=3)  # I don't care how many duties a week
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
                    cleaning_week = CleaningWeek.objects.create(week=week, schedule=schedule)
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
