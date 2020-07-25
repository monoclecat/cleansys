from rest_framework.viewsets import ModelViewSet
from rest_framework import generics, mixins, viewsets, permissions
from webinterface.models import *
from webinterface.serializers import *
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    The request is authenticated as a superuser, or is a read-only request.
    """
    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS or
            request.user and request.user.is_superuser
        )


class ScheduleViewSet(ModelViewSet):
    """
    API endpoint for Schedules. Each Schedule has a unique slug field.
    """
    queryset = Schedule.objects.enabled()
    serializer_class = ScheduleSerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrReadOnly]


class ScheduleGroupViewSet(ModelViewSet):
    """
    API endpoint that returns ScheduleGroups
    """
    queryset = ScheduleGroup.objects.all()
    serializer_class = ScheduleGroupSerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrReadOnly]


class CleanerViewSet(ModelViewSet):
    """
    API endpoint that returns Cleaners
    """
    queryset = Cleaner.objects.active()
    serializer_class = CleanerSerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=['GET'])
    def acceptable_dutyswitch(self, request, slug):
        cleaner = get_object_or_404(Cleaner, slug=slug)
        open_dutyswitch = DutySwitch.objects.open().all()
        acceptable = [x for x in open_dutyswitch if x.possible_acceptors().filter(cleaner=cleaner).exists()]
        serializer = DutySwitchSerializer(acceptable, many=True, context={'request': request})
        return Response(serializer.data)


class AffiliationViewSet(ModelViewSet):
    """
    API endpoint for Affiliations. Beginning and end are epoch weeks. Use API xyz to convert to date.
    """
    queryset = Affiliation.objects.all()
    serializer_class = AffiliationSerializer
    permission_classes = [IsAdminOrReadOnly]


class CleaningWeekViewSet(ModelViewSet):
    """
    API endpoint for CleaningWeek. CleaningWeeks are associated with a Schedule and bring Assignments and
    Tasks together.

    The field 'excluded' prevents Cleaners being assigned to this CleaningWeek.
    A Cleaner is added to this field when he had an Assignment in this week but switched it with someone else
    (prevents the Cleaner being switched back).
    """
    queryset = CleaningWeek.objects.all()
    serializer_class = CleaningWeekSerializer
    permission_classes = [IsAdminOrReadOnly]


class AssignmentViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments. Assignments link Cleaners with CleaningWeeks.
    CleaningWeeks contain the Tasks which must be done by its Assignments.
    """
    queryset = Assignment.objects.in_enabled_cleaning_weeks()  # Actually only the ones for a single Cleaner
    serializer_class = AssignmentSerializer
    permission_classes = [IsAdminOrReadOnly]


class TaskTemplateViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = TaskTemplate.objects.all()  # Actually only the ones for a single Schedule
    serializer_class = TaskTemplateSerializer
    permission_classes = [IsAdminOrReadOnly]


class TaskViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = Task.objects.all()  # Actually only the ones for a single CleaningWeek
    serializer_class = TaskSerializer
    permission_classes = [IsAdminOrReadOnly]


class DutySwitchViewSet(ModelViewSet):
    """
    API endpoint that returns Assignments
    """
    queryset = DutySwitch.objects.open()  # Actually only the ones which the Cleaner is able to accept
    serializer_class = DutySwitchSerializer
    permission_classes = [IsAdminOrReadOnly]
