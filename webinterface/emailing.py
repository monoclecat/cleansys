from webinterface.models import *
from markdown import markdown
from django.core import mail
from django.template.loader import get_template
from cleansys.settings import EMAIL_FROM_ADDRESS, BASE_URL_WITH_HOST


def send_email__new_acceptable_dutyswitch(dutyswitch: DutySwitch):
    cleaners = set(x.cleaner for x in dutyswitch.possible_acceptors()
                   if x.cleaner.email_pref_new_acceptable_dutyswitch and x.cleaner.user.email)
    outbox = []
    for cleaner in cleaners:
        tradeable_assignments = dutyswitch.possible_acceptors().filter(cleaner=cleaner).all()

        template = get_template('email_templates/email_new_acceptable_dutyswitch.md')
        context = {  # for base_template, context MUST contain cleaner and host
            'cleaner': cleaner,
            'host': BASE_URL_WITH_HOST,
            'dutyswitch': dutyswitch,
            'requester': dutyswitch.requester_assignment,
            'tradeable': tradeable_assignments,
        }
        plaintext = template.render(context)
        html = markdown(template.render(context), extensions=['tables'])
        msg = mail.EmailMultiAlternatives(
            "{} möchte einen Putzdienst tauschen".format(dutyswitch.requester_assignment.cleaner.name),
            plaintext, EMAIL_FROM_ADDRESS, [cleaner.user.email])
        msg.attach_alternative(html, "text/html")
        outbox.append(msg)
    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email__assignment_coming_up(notify_days_before=5):
    outbox = []
    for cleaner in Cleaner.objects.has_email().filter(email_pref_assignment_coming_up=True):
        assignments = cleaner.assignment_set.in_enabled_cleaning_weeks().\
            filter(cleaning_week__week__range=(current_epoch_week(), current_epoch_week()+1))

        notify = [x for x in assignments.all()
                  if x.assignment_date()-timezone.timedelta(days=notify_days_before) == timezone.now().date()]

        for assignment in notify:
            template = get_template('email_templates/email_assignment_coming_up.md')
            context = {  # for base_template, context MUST contain cleaner and host
                'cleaner': cleaner,
                'host': BASE_URL_WITH_HOST,
                'assignment': assignment,
            }
            plaintext = template.render(context)
            html = markdown(template.render(context), extensions=['tables'])
            msg = mail.EmailMultiAlternatives(
                "Dein Putzdienst in {} am {}".format(assignment.schedule,
                                                     assignment.assignment_date().strftime("%a, %d.%b.%Y")),
                plaintext, EMAIL_FROM_ADDRESS, [cleaner.user.email])
            msg.attach_alternative(html, "text/html")
            outbox.append(msg)
    connection = mail.get_connection()
    connection.send_messages(outbox)

