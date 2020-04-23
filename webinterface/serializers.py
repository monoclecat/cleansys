from rest_framework.serializers import *
from webinterface.models import *


def api_view_reference():
    return {
        'schedule': {'view_name': 'webinterface:api:schedule-detail', 'lookup_field': 'slug'},
        'user': {'view_name': 'webinterface:api:user-detail', 'lookup_field': 'username'},
        'cleaner': {'view_name': 'webinterface:api:cleaner-detail', 'lookup_field': 'slug'},
        'schedulegroup': {'view_name': 'webinterface:api:schedulegroup-detail', 'lookup_field': 'slug'},
        'affiliation': {'view_name': 'webinterface:api:affiliation-detail'},
        'cleaningweek': {'view_name': 'webinterface:api:cleaningweek-detail'},
        'assignment': {'view_name': 'webinterface:api:assignment-detail'},
        'tasktemplate': {'view_name': 'webinterface:api:tasktemplate-detail'},
        'task': {'view_name': 'webinterface:api:task-detail'},
        'dutyswitch': {'view_name': 'webinterface:api:dutyswitch-detail'},
    }


class ScheduleSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Schedule
        fields = ['url', 'id', 'slug', 'name', 'cleaners_per_date', 'weekday', 'frequency', 'disabled',
                  'tasktemplate_set', 'schedulegroup_set']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['schedule'],
            'tasktemplate_set': ref['tasktemplate'],
            'schedulegroup_set': ref['schedulegroup'],
        }


class ScheduleGroupSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ScheduleGroup
        fields = ['url', 'id', 'name', 'schedules', 'affiliation_set']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['schedulegroup'],
            'schedules': ref['schedule'],
            'affiliation_set': ref['affiliation'],
        }


class UserSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'id', 'username', 'email', 'cleaner']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['user'],
            'cleaner': ref['cleaner'],
        }


class CleanerSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Cleaner
        fields = ['url', 'id', 'user', 'name', 'affiliation_set', 'assignment_set']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['cleaner'],
            'user': ref['user'],
            'affiliation_set': ref['affiliation'],
            'assignment_set': ref['assignment'],
        }


class AffiliationSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Affiliation
        fields = ['url', 'id', 'cleaner', 'group', 'beginning', 'end']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['affiliation'],
            'cleaner': ref['cleaner'],
            'group': ref['schedulegroup']
        }


class CleaningWeekSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = CleaningWeek
        fields = ['url', 'id', 'week', 'excluded', 'schedule', 'assignments_valid', 'assignment_set',
                  'disabled', 'task_set']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['cleaningweek'],
            'excluded': ref['cleaner'],
            'schedule': ref['schedule'],
            'assignment_set': ref['assignment'],
            'task_set': ref['task'],
        }


class AssignmentSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Assignment
        fields = ['url', 'id', 'cleaner', 'cleaning_week', 'schedule']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['assignment'],
            'cleaner': ref['cleaner'],
            'cleaning_week': ref['cleaningweek'],
            'schedule': ref['schedule'],
        }


class TaskTemplateSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = TaskTemplate
        fields = ['url', 'id', 'name', 'help_text', 'start_days_before', 'end_days_after', 'schedule']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['tasktemplate'],
            'schedule': ref['schedule'],
        }


class TaskSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = ['cleaning_week', 'cleaned_by', 'template']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['task'],
            'cleaning_week': ref['cleaningweek'],
            'cleaned_by': ref['cleaner'],
            'template': ref['tasktemplate'],
        }


class DutySwitchSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = DutySwitch
        fields = ['created', 'requester_assignment', 'message']
        ref = api_view_reference()
        extra_kwargs = {
            'url': ref['dutyswitch'],
            'requester_assignment': ref['assignment'],
        }
