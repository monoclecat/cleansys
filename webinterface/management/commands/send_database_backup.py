from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMessage
from cleansys.settings import ADMINS, DATABASES


class Command(BaseCommand):
    help = 'Sends the database db.sqlite3 by email to the ADMINs mentioned in settings.'

    def handle(self, *args, **options):
        if not ADMINS:
            CommandError("ADMINS setting is not set!")
        if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in ADMINS):
            CommandError('The ADMINS setting must be a list of 2-tuples.')
        email = EmailMessage(
            subject="Backup of CleanSys database",
            body="Hello! \n\n"
                 "This is your cleaning-schedule management system CleanSys sending you a backup of the "
                 "database at its current state. \n\n\n"
                 "Best regards, \n\n"
                 "CleanSys \n\n\n\n",
            to=[x[1] for x in ADMINS]
        )
        email.attach_file(DATABASES['default']['NAME'])
        try:
            email.send(fail_silently=False)
        except Exception as e:
            CommandError(str(e))
