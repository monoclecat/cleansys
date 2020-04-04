from rest_framework.serializers import *
from webinterface.models import *


class ScheduleSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Schedule
        fields = ['name', 'cleaners_per_date', 'weekday', 'frequency', 'disabled']  # Also TaskTemplates!


class ScheduleGroupSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ScheduleGroup
        fields = ['name', 'schedules']


class CleanerSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Cleaner
        fields = ['user', 'name']


class AssignmentSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Assignment
        fields = ['cleaner', 'cleaning_week', 'schedule']  # task_set?


class TaskTemplateSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = TaskTemplate
        fields = ['task_name', 'task_help_text', 'start_days_before', 'end_days_after', 'schedule']


class TaskSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = ['cleaning_week', 'cleaned_by', 'template']


class DutySwitchSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = DutySwitch
        fields = ['created', 'requester_assignment', 'message']
