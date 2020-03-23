from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.http import Http404
from django.views.generic.list import ListView
from .forms import *
from .models import *


class ConfigView(TemplateView):
    template_name = 'webinterface/config.html'

    def get_context_data(self, **kwargs):
        context = super(ConfigView, self).get_context_data(**kwargs)
        context['active_schedule_list'] = Schedule.objects.enabled()
        context['disabled_schedule_list'] = Schedule.objects.disabled()

        context['active_cleaner_list'] = Cleaner.objects.active()
        context['inactive_cleaner_list'] = Cleaner.objects.inactive()

        context['active_schedule_group_list'] = ScheduleGroup.objects.enabled()
        context['disabled_schedule_group_list'] = ScheduleGroup.objects.disabled()
        return context


class ScheduleView(TemplateView):
    template_name = "webinterface/schedule.html"

    def get(self, request, *args, **kwargs):
        context = {}
        try:
            context['schedule'] = Schedule.objects.get(slug=kwargs['slug'])
        except Schedule.DoesNotExist:
            Http404("Putzplan existiert nicht.")

        cleaning_weeks = context['schedule'].cleaningweek_set.order_by('week')
        elements_per_page = 5

        if 'page' not in kwargs:
            if cleaning_weeks.filter(week__gt=current_epoch_week()).exists():
                index_of_current_cleaning_week = next(i for i, v
                                                      in enumerate(cleaning_weeks)
                                                      if v.week >= current_epoch_week())
                page_nr_with_current_cleaning_week = 1 + (index_of_current_cleaning_week // elements_per_page)
            else:
                page_nr_with_current_cleaning_week = 1
            return redirect(reverse_lazy('webinterface:schedule-view',
                                         kwargs={'slug': kwargs['slug'], 'page': page_nr_with_current_cleaning_week}))

        pagination = Paginator(cleaning_weeks, elements_per_page)
        context['page'] = pagination.get_page(kwargs['page'])

        if 'highlight_slug' in kwargs and kwargs['highlight_slug']:
            context['highlight_slug'] = kwargs['highlight_slug']

        if not request.user.is_superuser and 'highlight_slug' not in context:
            try:
                context['highlight_slug'] = Cleaner.objects.get(user=request.user)
            except Cleaner.DoesNotExist:
                pass

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if 'toggle_cleaning_week_active_status' in request.POST:
            pass
            # if 'source_assignment_pk' in request.POST and request.POST['source_assignment_pk']:
            #     try:
            #         source_assignment = Assignment.objects.get(pk=request.POST['source_assignment_pk'])
            #         duty_to_switch = DutySwitch.objects.create(source_assignment=source_assignment)
            #         duty_to_switch.look_for_destinations()
            #         return HttpResponseRedirect(reverse_lazy(
            #             'webinterface:switch-duty', kwargs={'pk': duty_to_switch.pk}))
            #     except (Cleaner.DoesNotExist, Assignment.DoesNotExist):
            #         raise SuspiciousOperation("Invalid PKs")
            # else:
            #     raise SuspiciousOperation("Invalid POST data sent by client")
        # elif 'clean' in request.POST:
        #     if 'source_assignment_pk' in request.POST and request.POST['source_assignment_pk']:
        #         try:
        #             assignment = Assignment.objects.get(pk=request.POST['source_assignment_pk'])
        #             if not assignment.cleaning_day.task_set.all():
        #                 assignment.cleaning_day.initiate_tasks()
        #                 assignment.cleaning_day.save()
        #
        #             return HttpResponseRedirect(reverse_lazy(
        #                 'webinterface:clean-duty', kwargs={'assignment_pk': assignment.pk}))
        #
        #         except Assignment.DoesNotExist:
        #             raise SuspiciousOperation("Invalid Assignment PK")
        # else:
        #     raise SuspiciousOperation("POST sent that didn't match a catchable case!")

        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view', kwargs={'slug': kwargs['slug'],
                                                                                       'page': kwargs['page']}))


class ScheduleList(ListView):
    template_name = "webinterface/schedule_list.html"
    model = Schedule

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            self.queryset = Schedule.objects.enabled()
        else:
            try:
                current_affiliation = Cleaner.objects.get(user=request.user).current_affiliation()
                if current_affiliation:
                    self.queryset = current_affiliation.group.schedules.enabled()
                else:
                    return Http404("Putzer ist nicht aktiv.")
            except Cleaner.DoesNotExist:
                return Http404("Putzer existiert nicht!")
        return super().get(request, *args, **kwargs)


class ScheduleTaskList(ListView):
    template_name = "webinterface/schedule_task_list.html"
    model = Task

    def __init__(self, *args, **kwargs):
        self.schedule = None
        super().__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            try:
                self.schedule = Schedule.objects.get(pk=kwargs['pk'])
                self.queryset = self.schedule.tasktemplate_set
            except Schedule.DoesNotExist:
                return Http404('Putzplan existiert nicht!')
        return super().get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        context['schedule'] = self.schedule
        return super().render_to_response(context, **response_kwargs)


class CleanerView(TemplateView):
    template_name = "webinterface/cleaner.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('webinterface:config'))
        try:
            cleaner = Cleaner.objects.get(user=request.user)
        except Cleaner.DoesNotExist:
            return Http404("Putzer existiert nicht")

        timezone.activate(cleaner.time_zone)

        context = dict()
        context['table_header'] = Schedule.objects.all().order_by('frequency')
        context['cleaner'] = cleaner

        assignments = context['cleaner'].assignment_set.order_by('cleaning_week__week')
        elements_per_page = 5

        if 'page' not in kwargs:
            if assignments.filter(cleaning_week__week__gt=current_epoch_week()).exists():
                index_of_current_cleaning_week = next(i for i, v
                                                      in enumerate(assignments)
                                                      if v.cleaning_week.week >= current_epoch_week())
                page_nr_with_current_assignments = 1 + (index_of_current_cleaning_week // elements_per_page)
            else:
                page_nr_with_current_assignments = 1
            return redirect(reverse_lazy('webinterface:cleaner',
                                         kwargs={'page': page_nr_with_current_assignments}))

        pagination = Paginator(assignments, elements_per_page)
        context['page'] = pagination.get_page(kwargs['page'])

        context['answerable_dutyswitch_requests'] = []
        for dutyswitch in DutySwitch.objects.open().all():
            if cleaner.can_accept_duty_switch_request(dutyswitch):
                context['answerable_dutyswitch_requests'].append(dutyswitch)

        return self.render_to_response(context)


class AssignmentTasksView(TemplateView):
    template_name = "webinterface/assignment_tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['assignment'] = Assignment.objects.get(pk=self.kwargs['assignment_pk'])
        except CleaningWeek.DoesNotExist:
            raise Http404("Assignment doesn't exist!")
        try:
            context['tasks'] = context['assignment'].cleaning_week.task_set.all()
        except CleaningWeek.DoesNotExist:
            logging.error("CleaningWeek does not exist on date!")
            raise Exception("CleaningWeek does not exist on date!")

        if 'schedule_page' in self.kwargs:
            context['schedule_page'] = self.kwargs['schedule_page']
        else:
            context['schedule_page'] = -1
        if 'cleaner_page' in self.kwargs:
            context['cleaner_page'] = self.kwargs['cleaner_page']
        else:
            context['cleaner_page'] = -1
        return context


class LoginByClickView(LoginView):
    template_name = "webinterface/login_byclick.html"
    extra_context = {'cleaner_list': Cleaner.objects.active()}
