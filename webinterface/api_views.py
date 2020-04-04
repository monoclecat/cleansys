from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from webinterface.models import *
from webinterface.serializers import *


class ScheduleViewSet(ModelViewSet):
    """
    API endpoint that returns Schedules
    """
    queryset = Schedule.objects.enabled()
    serializer_class = ScheduleSerializer


class ScheduleGroupViewSet(ModelViewSet):
    """
    API endpoint that returns ScheduleGroups
    """
    queryset = ScheduleGroup.objects.all()
    serializer_class = ScheduleGroupSerializer


class CleanerViewSet(ModelViewSet):
    """
    API endpoint that returns Cleaners
    """
    queryset = Cleaner.objects.active()
    serializer_class = CleanerSerializer


class AssignmentViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = Assignment.objects.all()  # Actually only the ones for a single Cleaner
    serializer_class = AssignmentSerializer


class TaskTemplateViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = TaskTemplate.objects.all()  # Actually only the ones for a single Schedule
    serializer_class = TaskTemplateSerializer


class TaskViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = Task.objects.all()  # Actually only the ones for a single CleaningWeek
    serializer_class = TaskSerializer


class DutySwitchViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = DutySwitch.objects.all()  # Actually only the ones which the Cleaner is able to accept
    serializer_class = AssignmentSerializer
