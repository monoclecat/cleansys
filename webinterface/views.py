import plotly.offline as opy
import plotly.graph_objs as go
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
from webinterface.models import *
import markdown


def back_button_page_context(kwargs: dict) -> dict:
    context = {}
    if 'schedule_page' in kwargs:
        context['back_to_schedule_page'] = kwargs['schedule_page']
    else:
        context['back_to_schedule_page'] = -1
    if 'cleaner_page' in kwargs:
        context['back_to_cleaner_page'] = kwargs['cleaner_page']
    else:
        context['back_to_cleaner_page'] = -1
    return context


class DocumentationView(TemplateView):
    template_name = 'webinterface/docs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with open('documentation/doc_main.md', 'r') as file:
            context['content'] = markdown.markdown(text=file.read(), output_format='html5', tab_length=2)
        return context


class AdminView(TemplateView):
    template_name = 'webinterface/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        enabled_schedules = Schedule.objects.enabled()
        # webinterface_snippets/schedule_panel.html needs to cover the same cases!
        context['action_needed_schedules'] = \
            set(enabled_schedules.filter(tasktemplate__isnull=True)) | \
            set(enabled_schedules.filter(assignment__isnull=True)) | \
            set(enabled_schedules.filter(schedulegroup__isnull=True)) | \
            set(x for x in Schedule.objects.enabled() if x.cleaningweek_set.assignments_invalid().exists()) | \
            set(x for x in Schedule.objects.enabled() if x.assignments_are_running_out())

        action_needed_schedule_pks = [x.pk for x in context['action_needed_schedules']]
        context['active_schedule_list'] = enabled_schedules.exclude(pk__in=action_needed_schedule_pks)
        context['disabled_schedule_list'] = Schedule.objects.disabled()

        # webinterface_snippets/cleaner_panel.html needs to cover the same cases!
        context['action_needed_cleaners'] = \
            Cleaner.objects.filter(affiliation__isnull=True)
        action_needed_cleaner_pks = [x.pk for x in context['action_needed_cleaners']]
        context['active_cleaner_list'] = Cleaner.objects.active().exclude(pk__in=action_needed_cleaner_pks)
        context['inactive_cleaner_list'] = Cleaner.objects.inactive().exclude(pk__in=action_needed_cleaner_pks)

        context['schedule_group_list'] = ScheduleGroup.objects.all()
        return context


class ScheduleView(ListView):
    template_name = "webinterface/schedule.html"
    model = CleaningWeek
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        self.schedule = get_object_or_404(Schedule, slug=kwargs['slug'])
        self.cleaning_weeks = self.schedule.cleaningweek_set.all()

        if 'page' not in kwargs:
            if self.cleaning_weeks.filter(week__gt=current_epoch_week()).exists():
                index_of_current_cleaning_week = next(i for i, v
                                                      in enumerate(self.cleaning_weeks)
                                                      if v.week >= current_epoch_week())
                page_nr_with_current_cleaning_week = 1 + (index_of_current_cleaning_week // self.paginate_by)
            else:
                page_nr_with_current_cleaning_week = 1
            return redirect(reverse_lazy('webinterface:schedule',
                                         kwargs={'slug': kwargs['slug'], 'page': page_nr_with_current_cleaning_week}))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.cleaning_weeks

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedule'] = self.schedule
        return context


class ScheduleAnalyticsView(DetailView):
    model = Schedule
    template_name = 'webinterface/schedule_analytics_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = {**context, **back_button_page_context(self.kwargs)}

        weeks = [x['week'] for x in self.object.cleaningweek_set.values("week")]
        weeks.sort()

        data = {}
        for week in weeks:
            cleaners__ratios = self.object.deployment_ratios(week=week)
            for cleaner, ratio in cleaners__ratios:
                if cleaner.name not in data:
                    data[cleaner.name] = {'weeks': [], 'ratios': []}
                data[cleaner.name]['weeks'].append(week)
                data[cleaner.name]['ratios'].append(ratio)

        fig = go.Figure()
        for cleaner, weeks__ratios in data.items():
            fig.add_trace(go.Scatter(
                x=[epoch_week_to_sunday(x) for x in weeks__ratios['weeks']],
                y=weeks__ratios['ratios'],
                name=cleaner,
                connectgaps=True
            ))

        fig.update_layout(title='Besetzungsverhältnisse',
                          xaxis_title='Wochen',
                          yaxis={'title': 'Besetzungsverhältnis',
                                 'range': [0.0, 1.0]})

        div = opy.plot(fig, auto_open=False, output_type='div')

        context['ratios'] = div
        return context


class SchedulePrintView(TemplateView):
    template_name = "webinterface/schedule_print.html"

    def get_context_data(self, **kwargs):
        schedule = Schedule.objects.get(slug=kwargs['slug'])
        context = {'schedule': schedule,
                   'cleaning_weeks': schedule.cleaningweek_set.filter(week__gte=kwargs['week']).order_by('week'),
                   'task_templates': schedule.tasktemplate_set.all()}
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
    paginate_by = 5

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('webinterface:admin'))
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
        context['answerable_dutyswitch_requests'] = []
        for duty_switch in DutySwitch.objects.all():
            if duty_switch.possible_acceptors().filter(cleaner=self.cleaner).exists():
                context['answerable_dutyswitch_requests'].append(duty_switch)

        return context


class CleanerAnalyticsView(ListView):
    model = Cleaner
    template_name = 'webinterface/cleaner_analytics_dashboard.html'

    def get_queryset(self):
        return Cleaner.objects.active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = {**context, **back_button_page_context(self.kwargs)}

        weeks = [x['week'] for x in CleaningWeek.objects.all().values("week")]
        weeks.sort()

        fig = go.Figure()
        for cleaner in context['cleaner_list']:
            fig.add_trace(go.Scatter(
                x=[epoch_week_to_sunday(x) for x in weeks],
                y=[cleaner.assignment_set.filter(cleaning_week__week=x).count() for x in weeks],
                name=cleaner.name,
                mode='lines+markers'
            ))

        fig.update_layout(title='Anzahl Putzdienste',
                          xaxis={'title': 'Wochen'},
                          yaxis={'title': 'Anzahl Putzdienste'})
        context['plot'] = opy.plot(fig, auto_open=False, output_type='div')

        return context


class AssignmentTasksView(TemplateView):
    template_name = "webinterface/assignment_tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = {**context, **back_button_page_context(self.kwargs)}

        try:
            cleaning_week = CleaningWeek.objects.get(pk=self.kwargs['cleaning_week_pk'])
        except CleaningWeek.DoesNotExist:
            logging.error("CleaningWeek does not exist on date!")
            raise Exception("CleaningWeek does not exist on date!")
        context['cleaning_week'] = cleaning_week
        context['schedule'] = cleaning_week.schedule
        context['tasks'] = cleaning_week.task_set.all()

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['cleaner_list'] = Cleaner.objects.active()
        return context
