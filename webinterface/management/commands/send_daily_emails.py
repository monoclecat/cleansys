from django.core.management.base import BaseCommand
from webinterface.email_sending import send_email__assignment_coming_up, send_email__warn_admin_tasks_forgotten


class Command(BaseCommand):
    help = 'Call multiple functions which may send emails if their conditions are met. ' \
           'Calls the send_email__assignment_coming_up() function in webinterface.emailing ' \
           'which notifies Cleaners of upcoming Assignments when these are 5 days away. '

    def handle(self, *args, **options):
        send_email__assignment_coming_up(notify_days_before=5)
        send_email__warn_admin_tasks_forgotten()
