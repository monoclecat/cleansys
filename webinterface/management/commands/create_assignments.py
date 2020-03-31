from django.core.management.base import BaseCommand, CommandError
from webinterface.models import *
from cleansys.settings import WARN_WEEKS_IN_ADVANCE__ASSIGNMENTS_RUNNING_OUT
import random


class Command(BaseCommand):
    help = 'Creates Assignments in all enabled Schedules by calling create_assignments_over_timespan() on each ' \
           'enabled Schedule. The timespan arguments start_week and end_week are current_epoch_week() and ' \
           'current_epoch_week() + -weeks-ahead. -weeks-ahead has a good default value ' \
           'so it doesn\'t need to be set necessarily.' \
           'When called by a Cronjob, it is sufficient to run this command once a week. ' \
           'This command only creates Assignments where there are ones missing or in ' \
           'CleaningWeeks where the assignments_valid field is False. ' \
           'Existing, valid Assignments are left alone, so there is no problem in running this command over the same' \
           'timespan multiple times.'

    def add_arguments(self, parser):
        parser.add_argument('-weeks-ahead', nargs='*', type=int,
                            help="The number of weeks from now to create Assignments in. "
                                 "Defaults to WARN_WEEKS_IN_ADVANCE__ASSIGNMENTS_RUNNING_OUT + 4.")

    def handle(self, *args, **options):
        if options['weeks_ahead'] is not None and options['weeks_ahead'] and options['weeks_ahead'] >= 0:
            weeks_ahead = options['weeks_ahead'][0]
        else:
            weeks_ahead = WARN_WEEKS_IN_ADVANCE__ASSIGNMENTS_RUNNING_OUT + 4

        for schedule in Schedule.objects.enabled():
            schedule.create_assignments_over_timespan(current_epoch_week(), current_epoch_week() + weeks_ahead)



