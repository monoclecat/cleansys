from django.core.management.base import BaseCommand
from webinterface.models import *
from cleansys.settings import WARN_WEEKS_IN_ADVANCE__ASSIGNMENTS_RUNNING_OUT


class Command(BaseCommand):
    help = 'Processes proposals for DutySwitch acceptors. When DutySwitch objects have gone several days without ' \
           'someone responding to them and accepting them, this command will propose an acceptor for the DutySwitch' \
           'object. The Cleaner of the proposed Assignment will get an email. If the Cleaner doesn\'t click the ' \
           'link to object to the proposal, this command will fulfill proposal after a certain amount of days.'

    def add_arguments(self, parser):
        parser.add_argument('-days-until-proposal', nargs='*', type=int,
                            help="The number of days a DutySwitch object must be old before this command "
                                 "proposes an acceptor.")
        parser.add_argument('-days-until-execution', nargs='*', type=int,
                            help="The number of days a proposal must be old before this command "
                                 "sets the proposed assignment as the acceptor.")

    def handle(self, *args, **options):
        if options['days_until_proposal'] and options['days_until_proposal'][0] >= 0:
            days_until_proposal = options['days_until_proposal'][0]
        else:
            days_until_proposal = 2

        if options['days_until_execution'] and options['days_until_execution'][0] >= 0:
            days_until_execution = options['days_until_execution'][0]
        else:
            days_until_execution = 2

        need_proposal = DutySwitch.objects.\
            filter(created__lt=timezone.now().date() - timezone.timedelta(days=days_until_proposal)).\
            filter(proposed_acceptor__isnull=True)

        [x.set_new_proposal() for x in need_proposal]

        execute_proposal = DutySwitch.objects.\
            filter(execute_proposal__lt=timezone.now().date() - timezone.timedelta(days=days_until_execution)).\
            exclude(proposed_acceptor__isnull=True)

        [x.set_proposal_as_acceptor() for x in execute_proposal]

