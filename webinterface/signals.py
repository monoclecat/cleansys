from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from webinterface.models import *


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


# This has been disabled because the Cleaner can select a proposed_acceptor in the DutySwitchCreateView.
# If the DutySwitch would then be resolved with a different Assignment, this might lead to frustration and confusion.
# @receiver(signal=m2m_changed, sender=DutySwitch.acceptor_weeks.through)
# def automatic_dutyswitch_accepting(instance: DutySwitch, action, model, pk_set, **kwargs):
#     if action == 'post_add':
#         instance_can_accept = instance.possible_acceptors().all()
#         open_dutyswitch_requests = DutySwitch.objects.open().\
#             filter(requester_assignment__in=instance_can_accept)
#
#         can_accept_instance = [x for x in open_dutyswitch_requests
#                                if instance.requester_assignment in x.possible_acceptors()]
#
#         if can_accept_instance:
#             # We set the acceptor of the other DutySwitch object, so that the emails make sense,
#             # as it then tells the other Cleaner that the Cleaner of instance accepted it.
#             can_accept_instance[0].acceptor_assignment = instance.requester_assignment
#             can_accept_instance[0].save()
#     return
