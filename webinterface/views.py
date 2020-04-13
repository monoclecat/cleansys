import plotly.offline as opy
import plotly.graph_objs as go
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.http import Http404
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.shortcuts import get_object_or_404
from webinterface.models import *
from cleansys import settings
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


def create_cleaner_analytics(weeks_into_past=20, weeks_into_future=20, recreate=False):
    """
    This function creates the offline plotly html file which is included in CleanerAnalyticsView

    :param weeks_into_past: Take CleaningWeeks from this many weeks back relative to the current week
    :param weeks_into_future: Same as weeks_into_past, just into the future
    :param recreate: If False, only missing plots will be created
    :return: None
    """
    # Cleaner analytics plots
    if recreate or not os.path.isfile(settings.CLEANER_ANALYTICS_FILE):
        weeks = set(x['week'] for x in CleaningWeek.objects.filter(
            week__range=(current_epoch_week() - weeks_into_past, current_epoch_week() + weeks_into_future)).values(
            "week"))
        weeks = list(weeks)
        weeks.sort()

        fig = go.Figure()
        for cleaner in Cleaner.objects.all():
            fig.add_trace(go.Scatter(
                x=[epoch_week_to_sunday(x) for x in weeks],
                y=[cleaner.assignment_set.filter(cleaning_week__week=x).count() for x in weeks],
                name=cleaner.name,
                mode='lines+markers'
            ))

        fig.update_layout(title='Anzahl Putzdienste',
                          xaxis={'title': 'Wochen'},
                          yaxis={'title': 'Anzahl Putzdienste'})
        plot_html = opy.plot(fig, auto_open=False, output_type='div')

        if os.path.isfile(settings.CLEANER_ANALYTICS_FILE):
            os.remove(settings.CLEANER_ANALYTICS_FILE)
        with open(settings.CLEANER_ANALYTICS_FILE, "w") as file:
            file.write(plot_html)


def create_schedule_analytics(weeks_into_past=20, weeks_into_future=20, only=None, recreate=False):
    """
    This function creates the offline plotly html files which are included in CleanerAnalyticsView and
    ScheduleAnalyticsView

    :param weeks_into_past: Take CleaningWeeks from this many weeks back relative to the current week
    :param weeks_into_future: Same as weeks_into_past, just into the future
    :param only: List of file paths which should only be regarded. Allows creation of single plots
    :param recreate: If False, only missing plots will be created
    :return: None
    """
    for schedule in Schedule.objects.enabled():
        if only is not None and schedule.analytics_plot_path() not in only:
            continue
        if not recreate and os.path.isfile(schedule.analytics_plot_path()):
            continue

        weeks = [x['week']
                 for x in schedule.cleaningweek_set.filter(
                week__range=(current_epoch_week() - weeks_into_past,
                             current_epoch_week() + weeks_into_future)).values("week")]
        weeks.sort()

        data = {}
        for week in weeks:
            cleaners__ratios = schedule.deployment_ratios(week=week)
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
                connectgaps=True,
                mode='lines+markers'
            ))

        fig.update_layout(title='Besetzungsverhältnisse',
                          xaxis_title='Wochen',
                          yaxis={'title': 'Besetzungsverhältnis',
                                 'range': [0.0, 1.0]})

        plot_html = opy.plot(fig, auto_open=False, output_type='div')

        if os.path.isfile(schedule.analytics_plot_path()):
            os.remove(schedule.analytics_plot_path())
        with open(schedule.analytics_plot_path(), "w") as file:
            file.write(plot_html)


class MarkdownView(TemplateView):
    template_name = 'webinterface/markdown_view.html'
    markdown_file_path = ''
    title = ''
    create_toc = False
    toc_depth = '###'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        with open(self.markdown_file_path, 'r', encoding="utf-8") as file:
            if self.create_toc:
                content = []
                toc = []
                link_pk = 0
                for line in file:
                    for i in range(1, len(self.toc_depth) + 1):
                        if len(line) > i+1 and line[:i+1] == '#' * i + ' ':
                            link_name = line[i+1:].replace('\n', '')
                            link_pk += 1
                            link_id = '{}_{}'.format(str(link_pk), slugify(link_name))
                            content.append('<a id="{}"></a>\n'.format(link_id))
                            toc.append('{}- [{}](#{})\n'.format('    '*(i-1), link_name, link_id))
                            break
                    content.append(line)

                content = toc + content
                content = ''.join(content)
            else:
                content = file.read()
            context['content'] = markdown.markdown(text=content, output_format='html5')
        return context


class DocumentationView(MarkdownView):
    markdown_file_path = os.path.join(settings.BASE_DIR, 'documentation', 'doc_main.md')
    title = "Einführung"
    create_toc = True


class AdminFAQView(MarkdownView):
    markdown_file_path = os.path.join(settings.BASE_DIR, 'documentation', 'faq.md')
    title = "FAQ"
    create_toc = True


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
        create_schedule_analytics(only=context['schedule'].analytics_plot_path(), recreate=False)
        with open(context['schedule'].analytics_plot_path(), 'r') as plot:
            context['plot'] = plot.read()

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


class CleanerCalendarView(TemplateView):
    template_name = "webinterface/cleaner_calendar.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('webinterface:admin'))
        self.cleaner = get_object_or_404(Cleaner, user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = self.cleaner.assignment_set.filter(cleaning_week__week__gte=current_epoch_week()-1). \
            order_by('cleaning_week__week', 'schedule__weekday')
        assignments = list(assignments)

        context['calendar_header'] = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        context['calendar_rows'] = []

        all_tasks = Task.objects.filter(cleaning_week__in=[x.cleaning_week for x in assignments],
                                        cleaned_by__isnull=True)
        for week in range(min(current_epoch_week(), assignments[0].cleaning_week.week),
                    assignments[-1].cleaning_week.week):
            monday = epoch_week_to_monday(week)
            columns = []
            for weekday in range(0, 7):
                day = monday + timezone.timedelta(days=weekday)
                day_data = {
                    'date': day.strftime("%d.%m."),
                    'is_today': timezone.now().date() == day,
                    'assignments': [x for x in assignments if x.assignment_date() == day],
                    'task_ready': any(x.is_active_on_date(day) for x in all_tasks)
                }
                columns.append(day_data)
            context['calendar_rows'].append(columns)
        return context


class CleanerAnalyticsView(ListView):
    model = Cleaner
    template_name = 'webinterface/cleaner_analytics_dashboard.html'

    def get_queryset(self):
        return Cleaner.objects.active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = {**context, **back_button_page_context(self.kwargs)}
        create_cleaner_analytics(recreate=False)  # Skips if already there
        with open(settings.CLEANER_ANALYTICS_FILE, 'r') as plot:
            context['plot'] = plot.read()

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
        context['tasks'] = cleaning_week.task_set.order_by('-template__end_days_after')

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
