from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.http import Http404
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.shortcuts import get_object_or_404
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


class ScheduleView(ListView):
    template_name = "webinterface/schedule.html"
    model = CleaningWeek
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        self.schedule = get_object_or_404(Schedule, slug=kwargs['slug'])
        self.cleaning_weeks = self.schedule.cleaningweek_set.order_by('week')

        if 'page' not in kwargs:
            if self.cleaning_weeks.filter(week__gt=current_epoch_week()).exists():
                index_of_current_cleaning_week = next(i for i, v
                                                      in enumerate(self.cleaning_weeks)
                                                      if v.week >= current_epoch_week())
                page_nr_with_current_cleaning_week = 1 + (index_of_current_cleaning_week // self.paginate_by)
            else:
                page_nr_with_current_cleaning_week = 1
            return redirect(reverse_lazy('webinterface:schedule-view',
                                         kwargs={'slug': kwargs['slug'], 'page': page_nr_with_current_cleaning_week}))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.cleaning_weeks

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedule'] = self.schedule
        return context


class SchedulePrintView(TemplateView):
    template_name = "webinterface/schedule_print.html"

    def get_context_data(self, **kwargs):
        schedule = Schedule.objects.get(slug=kwargs['slug'])
        context = {'schedule': schedule,
                   'cleaning_weeks': schedule.cleaningweek_set.filter(week__gte=kwargs['week']).order_by('week'),
                   'task_templates': schedule.tasktemplate_set.enabled()}
        return context


class ScheduleList(ListView):
    template_name = "webinterface/schedule_list.html"
    model = Schedule

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            self.queryset = Schedule.objects.enabled()
        else:
            current_affiliation = get_object_or_404(Cleaner, user=request.user).current_affiliation()
            if current_affiliation:
                self.queryset = current_affiliation.group.schedules.enabled()
            else:
                return Http404("Putzer ist nicht aktiv.")
        return super().dispatch(request, *args, **kwargs)


class ScheduleTaskList(DetailView):
    template_name = "webinterface/schedule_task_list.html"
    model = Schedule


class CleanerView(ListView):
    template_name = "webinterface/cleaner.html"
    model = Assignment
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('webinterface:config'))
        self.cleaner = get_object_or_404(Cleaner, user=request.user)
        self.assignments = self.cleaner.assignment_set.order_by('cleaning_week__week', 'schedule__weekday')

        if 'page' not in kwargs:
            if self.assignments.filter(cleaning_week__week__gt=current_epoch_week()).exists():
                index_of_current_cleaning_week = next(i for i, v
                                                      in enumerate(self.assignments)
                                                      if v.cleaning_week.week >= current_epoch_week())
                page_nr_with_current_assignments = 1 + (index_of_current_cleaning_week // self.paginate_by)
            else:
                page_nr_with_current_assignments = 1
            return redirect(reverse_lazy('webinterface:cleaner',
                                         kwargs={'page': page_nr_with_current_assignments}))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.assignments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cleaner'] = self.cleaner
        return context


class AssignmentTasksView(TemplateView):
    template_name = "webinterface/assignment_tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            cleaning_week = CleaningWeek.objects.get(pk=self.kwargs['cleaning_week_pk'])
        except CleaningWeek.DoesNotExist:
            logging.error("CleaningWeek does not exist on date!")
            raise Exception("CleaningWeek does not exist on date!")
        context['cleaning_week'] = cleaning_week
        context['tasks'] = cleaning_week.task_set.all()

        if 'schedule_page' in self.kwargs:
            context['schedule_page'] = self.kwargs['schedule_page']
        else:
            context['schedule_page'] = -1
        if 'cleaner_page' in self.kwargs:
            context['cleaner_page'] = self.kwargs['cleaner_page']
        else:
            context['cleaner_page'] = -1

        cleaner_for_user = context['view'].request.user.cleaner_set
        if cleaner_for_user.exists():
            context['cleaner'] = cleaner_for_user.first()
            context['assignment'] = context['cleaner'].assignment_in_cleaning_week(cleaning_week)
        else:
            context['cleaner'] = None
            if cleaning_week.assignment_set.exists():
                context['assignment'] = cleaning_week.assignment_set.first()
            else:
                context['assignment'] = None
        return context


class LoginByClickView(LoginView):
    template_name = "webinterface/login_byclick.html"
    extra_context = {'cleaner_list': Cleaner.objects.active()}
