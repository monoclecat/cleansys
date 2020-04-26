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
