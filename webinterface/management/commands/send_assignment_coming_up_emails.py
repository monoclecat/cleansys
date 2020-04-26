from django.core.management.base import BaseCommand
from webinterface.emailing import send_email__assignment_coming_up


class Command(BaseCommand):
    help = 'Calls the send_email__assignment_coming_up() function in webinterface.emailing. ' \
           'Notifies Cleaners of upcoming Assignments when these are 5 days away. '

    def handle(self, *args, **options):
        send_email__assignment_coming_up(notify_days_before=5)
