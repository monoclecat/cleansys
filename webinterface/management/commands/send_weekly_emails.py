from django.core.management.base import BaseCommand
from webinterface.email_sending import send_email__warn_admin_assignments_running_out, \
    send_email__warn_admin_cleaner_soon_homeless


class Command(BaseCommand):
    help = 'Call multiple functions which may send emails if their conditions are met. ' \
           'Calls send_email__warn_admin_assignments_running_out() which notifies the Admin ' \
           'if Schedule.assignments_are_running_out() returns True for any enabled Schedule. ' \
           'Calls send_email__warn_admin_cleaner_soon_homeless() which notifies the Admin ' \
           'if a Cleaner is scheduled to move out soon. '

    def handle(self, *args, **options):
        send_email__warn_admin_assignments_running_out()
        send_email__warn_admin_cleaner_soon_homeless()
