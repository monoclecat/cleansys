from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from webinterface.models import *

from django.core import mail
from django.template.loader import get_template
from django.template import Context
from markdown import markdown
from cleansys.settings import EMAIL_FROM_ADDRESS, BASE_URL_WITH_HOST


@receiver(signal=m2m_changed, sender=ScheduleGroup.schedules.through)
def schedule_group_changed(instance, action, model, pk_set, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        if model == Schedule:
            schedules = Schedule.objects.filter(pk__in=pk_set)
        else:
            schedules = Schedule.objects.filter(pk=instance.pk)
        if schedules.exists():
            for schedule in schedules.all():
                [x.set_assignments_valid_field(False) for x in schedule.cleaningweek_set.in_future()]
    return


@receiver(signal=post_save, sender=DutySwitch)
def send_email__new_acceptable_dutyswitch(instance: DutySwitch, created, **kwargs):
    if created:
        cleaners = set(x.cleaner for x in instance.possible_acceptors()
                       if x.cleaner.email_pref_new_acceptable_dutyswitch and x.cleaner.user.email)
        outbox = []
        for cleaner in cleaners:
            tradeable_assignments = instance.possible_acceptors().filter(cleaner=cleaner).all()

            template = get_template('email_templates/email_new_acceptable_dutyswitch.md')
            context = {
                'cleaner': cleaner,
                'dutyswitch': instance,
                'requester': instance.requester_assignment,
                'tradeable': tradeable_assignments,
                'host': BASE_URL_WITH_HOST
            }
            plaintext = template.render(context)
            html = markdown(template.render(context))
            msg = mail.EmailMultiAlternatives(
                "{} möchte einen Putzdienst tauschen".format(instance.requester_assignment.cleaner.name),
                plaintext, EMAIL_FROM_ADDRESS, [cleaner.user.email])
            msg.attach_alternative(html, "text/html")
            outbox.append(msg)
        connection = mail.get_connection()
        connection.send_messages(outbox)
    return
