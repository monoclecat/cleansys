from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, QueryDict
from django.http.response import HttpResponseForbidden
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView, CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView
from django.core.exceptions import SuspiciousOperation
from django.http import Http404
from django.views.generic.list import ListView
from slackbot.slackbot import start_slack, slack_running

from .forms import *
from .models import *

import timeit
from operator import itemgetter
import logging
import datetime


class ScheduleList(ListView):
    template_name = "webinterface/schedule_list.html"
    model = Schedule

    def get(self, request, *args, **kwargs):
        try:
            self.queryset = Cleaner.objects.get(user=request.user).schedule_group.schedules.all()
        except Cleaner.DoesNotExist:
            logging.error("A logged in User, which is not an admin, is not associated to a Cleaner!")
            return Http404("Putzer existiert nicht")
        return super().get(request, *args, **kwargs)


class LoginByClickView(LoginView):
    template_name = "webinterface/login_byclick.html"
    extra_context = {'cleaner_list': Cleaner.objects.active()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if not Config.objects.first().trust_in_users:
                url = HttpResponseRedirect(reverse("webinterface:login"))
                get_vars = QueryDict(mutable=True)
                if 'next' in request.GET and request.GET['next']:
                    get_vars['next'] = request.GET['next']
                if 'username' in request.POST and request.POST['username']:
                    get_vars['username'] = request.POST['username']
                url['Location'] += "?"+get_vars.urlencode(safe="/")
                return url
            else:
                return self.form_valid(form)
        else:
            return self.form_invalid(form)


class TaskView(UpdateView):
    template_name = "webinterface/clean_duty.html"
    model = Assignment
    form_class = AssignmentForm
    pk_url_kwarg = "assignment_pk"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(TaskView, self).get_context_data(**kwargs)
        try:
            context['tasks'] = self.object.cleaning_day.task_set.all()
        except CleaningDay.DoesNotExist:
            logging.error("CleaningDay does not exist on date!")
            raise Exception("CleaningDay does not exist on date!")

        context['assignment'] = self.object
        return context

    def post(self, request, *args, **kwargs):
        try:
            assignment = Assignment.objects.get(pk=kwargs['assignment_pk'])
            self.success_url = reverse_lazy(
                    'webinterface:clean-duty',
                    kwargs={'assignment_pk': assignment.pk})
        except Assignment.DoesNotExist:
            raise SuspiciousOperation("Assignment does not exist.")
        self.object = self.get_object()

        if 'cleaned' in request.POST:
            try:
                assignment = Assignment.objects.get(pk=kwargs['assignment_pk'])
                task = Task.objects.get(pk=request.POST['task_pk'])

                if task.cleaned_by:
                    if task.cleaned_by == assignment:
                        task.cleaned_by = None
                    else:
                        context = self.get_context_data(**kwargs)
                        context['already_cleaned_error'] = "{} wurde in der Zwischenzeit schon von {} gemacht!".format(
                            task.name, task.cleaned_by.cleaner)
                        return self.render_to_response(context)
                else:
                    task.cleaned_by = assignment
                task.save()
                return HttpResponseRedirect(self.get_success_url())

            except (Task.DoesNotExist, Assignment.DoesNotExist):
                raise SuspiciousOperation("Task or Assignment does not exist.")
        else:
            return super().post(args, kwargs)


class DutySwitchView(DetailView):
    template_name = "webinterface/switch_duty.html"
    model = DutySwitch

    def dispatch(self, request, *args, **kwargs):
        self.extra_context = dict()
        duty_switch = self.get_object()
        if request.user == duty_switch.source_assignment.cleaner.user:
            self.extra_context['perspective'] = 'source'
        elif request.user == duty_switch.selected_assignment.cleaner.user:
            self.extra_context['perspective'] = 'selected'
        else:
            return HttpResponseForbidden("Du hast keinen Zugriff auf diese Seite.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            duty_switch = DutySwitch.objects.get(pk=kwargs['pk'])
        except DutySwitch.DoesNotExist:
            raise SuspiciousOperation("Diese Putzdienst-Tausch-Seite existiert nicht.")

        if 'redirect_cleaner_slug' not in request.POST:
            raise SuspiciousOperation("Redirect_cleaner_slug not sent!")

        if 'delete' in request.POST:
            duty_switch.delete()
        elif 'accept' in request.POST:
            duty_switch.selected_was_accepted()
        elif 'reject' in request.POST:
            duty_switch.selected_was_rejected()
            duty_switch.save()
        elif 'select' in request.POST:
            if 'selected' in request.POST:
                try:
                    duty_switch.set_selected(Assignment.objects.get(pk=request.POST['selected']))

                except Assignment.DoesNotExist:
                    raise SuspiciousOperation("Invalid Assignment PK")
            else:
                raise SuspiciousOperation("Selected not sent!")
        else:
            raise SuspiciousOperation("POST sent that didn't match a catchable case!")

        return HttpResponseRedirect(reverse_lazy('webinterface:cleaner', kwargs={'page': 1}))


class CleanerView(TemplateView):
    template_name = "webinterface/cleaner.html"

    def post(self, request, *args, **kwargs):
        if 'switch' in request.POST:
            if 'source_assignment_pk' in request.POST and request.POST['source_assignment_pk']:
                try:
                    source_assignment = Assignment.objects.get(pk=request.POST['source_assignment_pk'])
                    duty_to_switch = DutySwitch.objects.create(source_assignment=source_assignment)
                    duty_to_switch.look_for_destinations()
                    return HttpResponseRedirect(reverse_lazy(
                        'webinterface:switch-duty', kwargs={'pk': duty_to_switch.pk}))
                except (Cleaner.DoesNotExist, Assignment.DoesNotExist):
                    raise SuspiciousOperation("Invalid PKs")
            else:
                raise SuspiciousOperation("Invalid POST data sent by client")
        elif 'clean' in request.POST:
            if 'source_assignment_pk' in request.POST and request.POST['source_assignment_pk']:
                try:
                    assignment = Assignment.objects.get(pk=request.POST['source_assignment_pk'])
                    if not assignment.cleaning_day.task_set.all():
                        assignment.cleaning_day.initiate_tasks()
                        assignment.cleaning_day.save()

                    return HttpResponseRedirect(reverse_lazy(
                        'webinterface:clean-duty', kwargs={'assignment_pk': assignment.pk}))

                except Assignment.DoesNotExist:
                    raise SuspiciousOperation("Invalid Assignment PK")
        else:
            raise SuspiciousOperation("POST sent that didn't match a catchable case!")

        return HttpResponseRedirect(reverse_lazy(
            'webinterface:cleaner',
            kwargs={'slug': kwargs['slug'], 'page': kwargs['page']}))

    def get(self, request, *args, **kwargs):
        try:
            cleaner = Cleaner.objects.get(user=request.user)
        except Cleaner.DoesNotExist:
            if request.user.is_superuser:
                return HttpResponseRedirect(reverse_lazy(
                    'webinterface:config'))
            logging.error("A logged in User, which is not an admin, is not associated to a Cleaner!")
            return Http404("Putzer existiert nicht")

        if 'page' not in kwargs or int(kwargs['page']) <= 0:
            return redirect(
                reverse_lazy('webinterface:cleaner', kwargs={'page': 1}))

        timezone.activate(cleaner.time_zone)

        context = dict()
        context['table_header'] = Schedule.objects.all().order_by('frequency')
        context['cleaner'] = cleaner

        start_date = correct_dates_to_due_day(timezone.now().date() - timezone.timedelta(days=2))

        assignments = Assignment.objects.filter(
            cleaner=context['cleaner'], cleaning_day__date__gte=start_date + timezone.timedelta(days=7)).order_by('cleaning_day__date')

        pagination = Paginator(assignments, 25)
        context['page'] = pagination.get_page(kwargs['page'])

        context['assignments_due_now'] = Assignment.objects.filter(
            cleaner=context['cleaner'], cleaning_day__date=start_date)
        if context['assignments_due_now']:
            context['can_start_assignments_due_now'] = \
                datetime.date.today() >= context['assignments_due_now'].first().possible_start_date()

        return self.render_to_response(context)


class ScheduleView(TemplateView):
    template_name = "webinterface/schedule.html"

    def get(self, request, *args, **kwargs):
        context = {}
        try:
            context['schedule'] = Schedule.objects.get(slug=kwargs['slug'])
        except Schedule.DoesNotExist:
            Http404("Putzplan existiert nicht.")

        last_date = context['schedule'].assignment_set.filter(cleaning_day__date__lte=timezone.now().date())
        next_dates = context['schedule'].assignment_set.filter(
            cleaning_day__date__gte=timezone.now().date())

        assignments = list(last_date)[-1:] + list(next_dates)

        pagination = Paginator(assignments, 30*context['schedule'].cleaners_per_date)
        context['page'] = pagination.get_page(kwargs['page'])

        return self.render_to_response(context)


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ResultsForm

    def get_context_data(self, **kwargs):
        context = super(ConfigView, self).get_context_data(**kwargs)
        context['schedule_list'] = Schedule.objects.all()
        all_active_cleaners = Cleaner.objects.active()
        context['cleaner_list'] = all_active_cleaners.has_slack_id()
        context['no_slack_cleaner_list'] = all_active_cleaners.no_slack_id()
        context['deactivated_cleaner_list'] = Cleaner.objects.inactive()
        context['schedule_group_list'] = ScheduleGroup.objects.all()
        context['slack_running'] = slack_running()
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        if 'start_slack' in request.POST:
            if not slack_running():
                start_slack()
                return HttpResponseRedirect(reverse_lazy('webinterface:config'))

        form = self.get_form()

        if form.is_valid():
            start_date = datetime.datetime.strptime(request.POST['start_date'], '%d.%m.%Y').date()
            end_date = datetime.datetime.strptime(request.POST['end_date'], '%d.%m.%Y').date()

            results_kwargs = {'from_date': start_date.strftime('%d-%m-%Y'),
                              'to_date': end_date.strftime('%d-%m-%Y')}

            if 'show_deviations' in request.POST:
                results_kwargs['options'] = 'stats'
            return HttpResponseRedirect(reverse_lazy('webinterface:results', kwargs=results_kwargs))
        return self.form_invalid(form)


class ResultsView(TemplateView):
    template_name = 'webinterface/results.html'

    def post(self, request, *args, **kwargs):
        if 'regenerate_all' in request.POST:
            clear_existing = True
        else:
            clear_existing = False

        time_start = timeit.default_timer()
        for schedule in Schedule.objects.all():
            schedule.new_cleaning_duties(
                datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date(),
                datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date(),
                clear_existing)
        time_end = timeit.default_timer()
        logging.info("Assigning cleaning schedules took {}s".format(round(time_end-time_start, 2)))

        results_kwargs = {'from_date': kwargs['from_date'], 'to_date': kwargs['to_date']}

        if 'options' in kwargs:
            results_kwargs['options'] = kwargs['options']

        return HttpResponseRedirect(
            reverse_lazy('webinterface:results', kwargs=results_kwargs))

    def get(self, request, *args, **kwargs):
        from_date = datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date()
        to_date = datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date()

        context = dict()
        context['assignments_by_schedule'] = list()
        for schedule in Schedule.objects.all():
            context['assignments_by_schedule'].append(
                schedule.assignment_set.filter(cleaning_day__date__range=(from_date, to_date)))
        return self.render_to_response(context)


class ResultsViewOld(TemplateView):
    template_name = 'webinterface/results.html'

    def post(self, request, *args, **kwargs):
        if 'regenerate_all' in request.POST:
            clear_existing = True
        else:
            clear_existing = False

        time_start = timeit.default_timer()
        for schedule in Schedule.objects.all():
            schedule.new_cleaning_duties(
                datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date(),
                datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date(),
                clear_existing)
        time_end = timeit.default_timer()
        logging.info("Assigning cleaning schedules took {}s".format(round(time_end-time_start, 2)))

        results_kwargs = {'from_date': kwargs['from_date'], 'to_date': kwargs['to_date']}

        if 'options' in kwargs:
            results_kwargs['options'] = kwargs['options']

        return HttpResponseRedirect(
            reverse_lazy('webinterface:results', kwargs=results_kwargs))

    def get(self, request, *args, **kwargs):

        from_date_raw = datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date()
        to_date_raw = datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date()

        kwargs['from_date'], kwargs['to_date'] = correct_dates_to_due_day([from_date_raw, to_date_raw])

        if kwargs['to_date'] < kwargs['from_date']:
            temp_date = kwargs['from_date']
            kwargs['from_date'] = kwargs['to_date']
            kwargs['to_date'] = temp_date
        context = dict()

        context['schedules'] = Schedule.objects.all().order_by('frequency')

        context['dates'] = []
        date_iterator = kwargs['from_date']
        one_week = timezone.timedelta(days=7)
        while date_iterator <= kwargs['to_date']:
            context['dates'].append(date_iterator)
            date_iterator += one_week

        relevant_cleaners = Cleaner.objects.filter(moved_in__lt=kwargs['to_date'], moved_out__gt=kwargs['from_date'])
        moved_in_during_timeframe = sorted(relevant_cleaners.filter(
            moved_in__gte=kwargs['from_date']).values('pk', 'moved_in'), key=itemgetter('moved_in'))

        moved_out_during_timeframe = sorted(relevant_cleaners.filter(
            moved_out__lte=kwargs['to_date']).values('pk', 'moved_out'), key=itemgetter('moved_out'))

        move_ins_and_move_outs = []
        for move_in_event in moved_in_during_timeframe:
            if move_ins_and_move_outs:
                if correct_dates_to_due_day(move_in_event['moved_in']) == move_ins_and_move_outs[-1]['start_date']:
                    move_ins_and_move_outs[-1]['moved_in'].append(Cleaner.objects.get(pk=move_in_event['pk']))
                    continue
            move_ins_and_move_outs.append({'start_date': correct_dates_to_due_day(move_in_event['moved_in']),
                                           'moved_in': [Cleaner.objects.get(pk=move_in_event['pk'])], 'moved_out': []})

        for move_out_event in moved_out_during_timeframe:
            for move_in_event in move_ins_and_move_outs:
                if correct_dates_to_due_day(move_out_event['moved_out']) == \
                        move_in_event['start_date']:  # Here moved_out is a date
                    move_in_event['moved_out'].append(Cleaner.objects.get(pk=move_out_event['pk']))
                    break
            else:
                move_ins_and_move_outs.append({'start_date': correct_dates_to_due_day(move_out_event['moved_out']),
                                               'moved_in': [],
                                               'moved_out': [Cleaner.objects.get(pk=move_out_event['pk'])]})

        move_ins_and_move_outs = sorted(move_ins_and_move_outs, key=itemgetter('start_date'))

        context['results'] = []
        if move_ins_and_move_outs:
            if kwargs['from_date'] != move_ins_and_move_outs[0]['start_date']:
                context['results'].append({'start_date': kwargs['from_date'],
                                           'end_date': move_ins_and_move_outs[0]['start_date'] - one_week,
                                           'moved_in': [], 'moved_out': []})

            miamo_iterator = 1
            while miamo_iterator < len(move_ins_and_move_outs):
                move_ins_and_move_outs[miamo_iterator - 1]['end_date'] = \
                    move_ins_and_move_outs[miamo_iterator]['start_date'] - one_week
                miamo_iterator += 1
            move_ins_and_move_outs[-1]['end_date'] = kwargs['to_date']
        else:
            context['results'].append({'start_date': kwargs['from_date'],
                                       'end_date': kwargs['to_date'],
                                       'moved_in': [], 'moved_out': []})

        context['results'] += move_ins_and_move_outs

        for time_frame in context['results']:
            date_iterator = time_frame['start_date']
            time_frame['assignments'] = []
            while date_iterator <= time_frame['end_date']:
                assignments_on_date = [date_iterator]
                schedules = []
                for schedule in context['schedules']:
                    if schedule.defined_on_date(date_iterator):
                        assignments = schedule.assignment_set.filter(cleaning_day__date=date_iterator)
                        if assignments.exists():
                            cleaners_for_assignment = []
                            for assignment in assignments:
                                cleaners_for_assignment.append(assignment.cleaner.name)
                            schedules.append(cleaners_for_assignment)
                        else:
                            schedules.append("")
                    else:
                        schedules.append(".")
                    assignments_on_date.append(schedules)
                time_frame['assignments'].append(assignments_on_date)
                date_iterator += one_week

        if 'options' in kwargs and kwargs['options'] == 'stats':
            for time_frame in context['results']:
                time_frame['duty_counter'] = []
                time_frame['deviations_by_schedule'] = []
                for schedule in context['schedules']:
                    assignments_in_timeframe = schedule.assignment_set.filter(
                        cleaning_day__date__range=(time_frame['start_date'], time_frame['end_date']))

                    element = [schedule.name, 0, 0, []]

                    deviation_of = []
                    sum_deviation_values = 0
                    ratios = schedule.deployment_ratios(for_date=time_frame['end_date'])
                    if ratios:
                        for cleaner, ratio in ratios:
                            element[3].append([cleaner.name, assignments_in_timeframe.filter(cleaner=cleaner).count()])

                            deviation_of.append([cleaner, round(abs(1 - ratio), 3)])
                            sum_deviation_values += abs(1 - ratio)

                        element[3] = sorted(element[3], key=itemgetter(1), reverse=True)
                        element[1] = element[3][0][1]
                        element[2] = element[3][-1][1]
                        time_frame['duty_counter'].append(element)

                        schedule_data = [[schedule.name, round(sum_deviation_values / len(deviation_of), 3)]]
                        schedule_data.append(sorted(deviation_of, key=itemgetter(1), reverse=True))
                        time_frame['deviations_by_schedule'].append(schedule_data)

        return self.render_to_response(context)


class ConfigUpdateView(UpdateView):
    form_class = ConfigForm
    model = Config
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_object(self, queryset=None):
        return Config.objects.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere die Systemweite Konfiguration"
        return context


class CleanerNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Füge neuen Putzer hinzu"
        return context


class CleanerUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzerprofil"
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class CleanerDeleteView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzer"
        return context


class CleaningScheduleNewView(CreateView):
    form_class = CleaningScheduleForm
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erzeuge neuen Putzplan"
        return context


class CleaningScheduleUpdateView(UpdateView):
    form_class = CleaningScheduleForm
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzplan"
        return context


class CleaningScheduleDeleteView(DeleteView):
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzplan"
        return context


class CleaningScheduleGroupNewView(CreateView):
    form_class = CleaningScheduleGroupForm
    model = ScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erstelle eine neue Putzplan-Gruppierung"
        return context


class CleaningScheduleGroupUpdateView(UpdateView):
    form_class = CleaningScheduleGroupForm
    model = ScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere eine Putzplan-Gruppierung"
        return context


class CleaningScheduleGroupDeleteView(DeleteView):
    form_class = CleaningScheduleGroupForm
    model = ScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzplan-Gruppierung"
        return context
