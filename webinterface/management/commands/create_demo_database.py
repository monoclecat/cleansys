from django.core.management.base import BaseCommand, CommandError
from webinterface.models import *
import math
import random


class Command(BaseCommand):
    help = 'Populates an empty database with a rich demonstration ' \
           'featuring all types of objects and functionalities.' \
           'By default, the total timeframe of the demo spans 16 weeks (from <this week minus 3 weeks> up to ' \
           '<this week plus 12 weeks>).'

    def add_arguments(self, parser):
        parser.add_argument('-timeframe', nargs='*', type=int, help="Length of the demo time frame in weeks (integer). "
                                                                    "Must be >= 4.")
        parser.add_argument('--clear-db', nargs='*', help="Add this flag if you would like to delete all existing "
                                                          "objects (to have an empty database) before running.")

    def handle(self, *args, **options):
        if options['timeframe'] is not None and options['timeframe'] and options['timeframe'] >= 4:
            demo_length = options['timeframe'][0]
        else:
            demo_length = 16

        if options['clear_db'] is not None:
            clear_db = True
        else:
            clear_db = False

        def eval_model(model, delete: bool):
            obj = model.objects.all()
            if obj.exists():
                if delete:
                    self.stdout.write("Deleting {} objects...".format(model.__name__))
                    obj.delete()
                else:
                    raise CommandError("Found {} object! The database needs to be empty of objects "
                                       "in order to create the demo database!".format(model.__name__))

        eval_model(DutySwitch, clear_db)
        eval_model(Task, clear_db)
        eval_model(Assignment, clear_db)
        eval_model(TaskTemplate, clear_db)
        eval_model(CleaningWeek, clear_db)
        eval_model(Affiliation, clear_db)
        eval_model(Cleaner, clear_db)
        if clear_db:
            User.objects.filter(is_superuser=False).delete()
        eval_model(ScheduleGroup, clear_db)
        eval_model(Schedule, clear_db)

        self.stdout.write("Creating schedules...")
        sch1 = Schedule.objects.create(name="Bad EG", cleaners_per_date=1, weekday=6, frequency=1)
        sch2 = Schedule.objects.create(name="Bad 1. OG", cleaners_per_date=1, weekday=6, frequency=1)
        sch3 = Schedule.objects.create(name="Bad 2. OG", cleaners_per_date=1, weekday=6, frequency=1)
        sch4 = Schedule.objects.create(name="Küche EG & 1. OG", cleaners_per_date=2, weekday=5, frequency=1)
        sch5 = Schedule.objects.create(name="Küche 2. OG", cleaners_per_date=2, weekday=5, frequency=1)
        sch6 = Schedule.objects.create(name="Treppenhaus", cleaners_per_date=2, weekday=3, frequency=1)
        sch7 = Schedule.objects.create(name="Um Katze kümmern", cleaners_per_date=2, weekday=3, frequency=1)
        sch8 = Schedule.objects.create(name="Garten", cleaners_per_date=2, weekday=4, frequency=2)
        sch9 = Schedule.objects.create(name="Keller", cleaners_per_date=2, weekday=4, frequency=3)
        schd = Schedule.objects.create(name="Alter Plan", cleaners_per_date=2, weekday=4, frequency=3)


        self.stdout.write("Creating ScheduleGroups...")
        eg = ScheduleGroup.objects.create(name="Erdgeschoss")
        eg.schedules.add(sch1, sch4, sch6, sch7, sch8, sch9)
        og1 = ScheduleGroup.objects.create(name="1. Obergeschoss")
        og1.schedules.add(sch2, sch4, sch6, sch7, sch8, sch9)
        og2 = ScheduleGroup.objects.create(name="2. Obergeschoss")
        og2.schedules.add(sch3, sch5, sch6, sch7, sch8, sch9)
        dis_group = ScheduleGroup.objects.create(name="Alte Gruppe", disabled=True)
        dis_group.schedules.add(schd)

        self.stdout.write("Creating Cleaners...")
        cl_a = Cleaner.objects.create(name="Anne", preference=1)
        cl_b = Cleaner.objects.create(name="Bernd", preference=2)
        cl_c = Cleaner.objects.create(name="Clara", preference=3)
        cl_d = Cleaner.objects.create(name="Daniel", preference=1)
        cl_e = Cleaner.objects.create(name="Eric", preference=2)
        cl_f = Cleaner.objects.create(name="Franziska", preference=3)
        cl_g = Cleaner.objects.create(name="Gero", preference=1)
        cl_h = Cleaner.objects.create(name="Hannah", preference=2)
        cl_i = Cleaner.objects.create(name="Ina", preference=3)
        cl_j = Cleaner.objects.create(name="Justin", preference=1)
        cl_k = Cleaner.objects.create(name="Kim", preference=2)
        cl_l = Cleaner.objects.create(name="Luisa", preference=3)
        cl_m = Cleaner.objects.create(name="Marlene", preference=1)
        cl_n = Cleaner.objects.create(name="Nina", preference=2)
        cl_o = Cleaner.objects.create(name="Olaf", preference=3)
        cl_moved_out = Cleaner.objects.create(name="Ehemaliger")

        self.stdout.write("Creating TaskTemplates...")

        def create_task_templates(schedule: Schedule, template_tuples: list):
            for name, help_text, disabled, start, end in bathroom_tasks:
                TaskTemplate.objects.create(task_name=name, task_help_text=help_text, task_disabled=disabled,
                                            schedule=schedule,
                                            start_days_before=start, end_days_after=end)

        common_bathroom_kitchen_tasks = \
            [('Boden wischen', 'Wische den Boden. Verwende Allzweckreiniger im Putzwasser', False, 2, 2),
             ('Müll rausbringen', 'Bringe den Müll raus', False, 2, 2),
             ('Oberflächen', 'Wische die Oberflächen ab, damit sie Staub- und Schmutzfrei sind', False, 2, 2),
             ('Handtücher wechseln', 'Gib dem Bad frische Handtücher', False, 1, 4),
             ('Putzmittel auffüllen', 'Putzmittel leer? Neues her!', False, 1, 4),
             ('Putzlappen wecheln', 'Lasse die Putzlappen waschen', False, 1, 4),
             ('Dusche putzen', 'Schrubbe die Duschwände und hole die Haare aus dem Abfluss', False, 1, 4),
             ('Deaktivierte Aufgabe', 'Diese Aufgabe ist deaktiviert', True, 4, 4)]

        bathroom_tasks = \
            [('Waschbecken putzen', 'Wische das Waschbecken', False, 2, 2),
             ('Spiegel putzen', 'Putze den Spiegel mit Glasreiniger', False, 2, 2),
             ('Toilette putzen', 'Putze die Toilettenschüssel mit Reiniger und der Klobürste', False, 2, 2),
             ('Dusche putzen', 'Schrubbe die Duschwände und hole die Haare aus dem Abfluss', False, 1, 4)] + \
            common_bathroom_kitchen_tasks

        for sch in [sch1, sch2, sch3]:
            create_task_templates(schedule=sch, template_tuples=bathroom_tasks)

        kitchen_tasks = \
            [('Herd putzen', 'Schrubbe den Herd blitzeblank', False, 2, 2),
             ('Spülbecken putzen', 'Schrubbe die Spülbecken', False, 2, 2),
             ('Esstisch abwischen', 'Wische den Esstisch ab', False, 2, 2),
             ('Biomülleimer putzen', 'Putze den siffigen Biomüll-Eimer', False, 2, 2)] + \
            common_bathroom_kitchen_tasks

        for sch in [sch4, sch5]:
            create_task_templates(schedule=sch, template_tuples=kitchen_tasks)

        stairway_tasks = \
            [('Treppe fegen', 'Fege die Treppe, bevor du sie wischst', False, 2, 2),
             ('Treppe wischen', 'Wische die Treppe mit normalem Wasser (kein Reiniger!)', False, 2, 2),
             ('Handtücher waschen', 'Zum Treppenputzdienst gehört auch das Waschen aller Handtücher', False, 2, 2),
             ('Deaktivierte Aufgabe', 'Diese Aufgabe ist deaktiviert', True, 4, 4)]
        create_task_templates(schedule=sch6, template_tuples=stairway_tasks)

        meowmeow_tasks = \
            [('Futter auffüllen', 'Mietz will schließlich was zu essen haben', False, 2, 2),
             ('Katzenklo', 'Fisch die Brocken aus dem Streu', False, 2, 2),
             ('Wasser auffüllen', 'Und nochmal für alle: KEIN BIER', False, 2, 2),
             ('Deaktivierte Aufgabe', 'Diese Aufgabe ist deaktiviert', True, 4, 4)]
        create_task_templates(schedule=sch7, template_tuples=meowmeow_tasks)

        garden_tasks = \
            [('Rasen mähen', 'Fülle bitte Benzin nach wenn es fast leer ist!', False, 4, 2),
             ('Unkraut yeeten', 'Sonst wächst das Gemüse nicht gut', False, 4, 2),
             ('Kompost umgraben', 'Die unteren Schichten nach oben und umgekehrt', False, 2, 4),
             ('Deaktivierte Aufgabe', 'Diese Aufgabe ist deaktiviert', True, 4, 4)]
        create_task_templates(schedule=sch8, template_tuples=garden_tasks)

        basement_tasks = \
            [('Inventar machen', 'Schreibe bitte auf wie viel von jedem Getränk da ist', False, 2, 4),
             ('Boden fegen', 'Am besten Staubmaske tragen', False, 2, 4),
             ('Gaszähler lesen', 'Schreibe bitte den Stand in unser Buch', False, 4, 2),
             ('Deaktivierte Aufgabe', 'Diese Aufgabe ist deaktiviert', True, 4, 4)]
        create_task_templates(schedule=sch9, template_tuples=basement_tasks)

        # Create time-dependent objects, using current week number as reference so that you can see the difference
        # between cleaning week in past and in future
        now = current_epoch_week()

        self.stdout.write("Creating Affiliations...")

        def affiliate_cleaner(cleaner: Cleaner, groups: list):
            weeks_in_each_group = demo_length // len(groups)
            for j, group in enumerate(groups):
                Affiliation.objects.create(cleaner=cleaner, group=group,
                                           beginning=now + j * weeks_in_each_group - 3,
                                           end=now + ((j + 1) * weeks_in_each_group - 1) - 3)

        def affiliate_multiple_cleaners(cleaners: list, group_sequence: list):
            max_pow_of_2 = math.floor(math.log2(len(group_sequence)))
            for i, cleaner in enumerate(cleaners):
                groups_for_cleaner = group_sequence[:int(math.pow(2, (i % (max_pow_of_2 + 1))))]
                # We get [0:1], [0:2], [0:4], [0:1], [0:2],  [0:4], [0:1], etc.  when len(group_sequence)==4

                affiliate_cleaner(cleaner=cleaner, groups=groups_for_cleaner)

        # We have 15 cleaners which we split into 3 groups which will have similar Affiliation patterns
        affiliate_multiple_cleaners(cleaners=[cl_a, cl_b, cl_c, cl_d, cl_e], group_sequence=[eg, og1, og2, eg])
        affiliate_multiple_cleaners(cleaners=[cl_f, cl_g, cl_h, cl_i, cl_j], group_sequence=[og1, og2, eg, og1])
        affiliate_multiple_cleaners(cleaners=[cl_k, cl_l, cl_m, cl_n, cl_o], group_sequence=[og1, og2, eg, og1])
        Affiliation.objects.create(cleaner=cl_moved_out, group=dis_group, beginning=now-10, end=now-1)

        self.stdout.write("Creating Assignments (this can take some time)...")
        for sch in Schedule.objects.all():
            sch.create_assignments_over_timespan(start_week=now - 3, end_week=now - 3 + demo_length)

        self.stdout.write("Creating Tasks...")
        for cleaning_week in CleaningWeek.objects.all():
            cleaning_week.create_missing_tasks()

        self.stdout.write("Creating DutySwitch objects...")
        # Sprinkle some dutyswitch requests over the cleaning_weeks
        for cl in [cl_a, cl_d, cl_g, cl_j, cl_m]:
            assignments = Assignment.objects.filter(cleaner=cl,
                                                    cleaning_week__week__range=(now, now + demo_length - 3 - 4))
            for i in range(0, 2):
                choice = random.choice(assignments)
                DutySwitch.objects.create(requester_assignment=choice)
                assignments = assignments.exclude(pk=choice.pk)

        self.stdout.write("Last tweaks...")
        # Of course the Cleaners were diligent and did all tasks until now
        for task in Task.objects.filter(cleaning_week__week__range=(now - 3, now)):
            if task.has_passed() or task.my_time_has_come():
                possible_cl = task.possible_cleaners()
                if len(possible_cl) != 0:
                    task.set_cleaned_by(random.choice(possible_cl))

        # Except a couple of tasks which are chosen by random
        cleaned_tasks = Task.objects.exclude(cleaned_by__isnull=True)
        if len(cleaned_tasks) != 0:
            for i in range(0, 10):
                uncleaned_task = random.choice(cleaned_tasks)
                uncleaned_task.set_cleaned_by(None)
                cleaned_tasks = cleaned_tasks.exclude(pk=uncleaned_task.pk)




