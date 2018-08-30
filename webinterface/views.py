from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, QueryDict
from django.http.response import HttpResponseForbidden
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.core.paginator import Paginator
from django.views.generic.detail import DetailView
from django.core.exceptions import SuspiciousOperation
from django.http import Http404
from django.views.generic.list import ListView
from slackbot.slackbot import start_slack, slack_running

from .forms import *
from .models import *

import timeit
import logging
import datetime


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ResultsForm

    def get_context_data(self, **kwargs):
        context = super(ConfigView, self).get_context_data(**kwargs)
        context['active_schedule_list'] = Schedule.objects.enabled()
        context['disabled_schedule_list'] = Schedule.objects.disabled()

        context['cleaner_list'] = list()
        context['no_slack_cleaner_list'] = list()
        context['deactivated_cleaner_list'] = list()
        for cleaner in Cleaner.objects.all():
            if cleaner.is_active():
                if cleaner.slack_id:
                    context['cleaner_list'].append(cleaner)
                else:
                    context['no_slack_cleaner_list'].append(cleaner)
            else:
                context['deactivated_cleaner_list'].append(cleaner)

        context['active_schedule_group_list'] = ScheduleGroup.objects.enabled()
        context['disabled_schedule_group_list'] = ScheduleGroup.objects.disabled()
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

        today_corrected = correct_dates_to_due_day(timezone.now().date())

        assignments = Assignment.objects.filter(
            cleaner=context['cleaner'], cleaning_day__date__gte=today_corrected - timezone.timedelta(days=7))

        pagination = Paginator(assignments, 25)
        context['page'] = pagination.get_page(kwargs['page'])

        context['assignments_due_now'] = Assignment.objects.filter(
            cleaner=context['cleaner'], cleaning_day__date=today_corrected)
        if context['assignments_due_now']:
            context['can_start_assignments_due_now'] = \
                datetime.date.today() >= context['assignments_due_now'].first().possible_start_date()

        return self.render_to_response(context)


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


class LoginByClickView(LoginView):
    template_name = "webinterface/login_byclick.html"
    extra_context = {'cleaner_list': Cleaner.objects.active()}

    def post(self, request, *args, **kwargs):
        print(request.POST)
        return super().post(request, *args, **kwargs)


class ResultsView(TemplateView):
    template_name = 'webinterface/results.html'

    def post(self, request, *args, **kwargs):
        if 'regenerate_all' in request.POST:
            mode = 1
        else:
            mode = 2

        time_start = timeit.default_timer()
        for schedule in Schedule.objects.all():
            schedule.new_cleaning_duties(
                datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date(),
                datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date(),
                mode)
        time_end = timeit.default_timer()
        logging.info("Assigning cleaning schedules took {}s".format(round(time_end-time_start, 2)))

        results_kwargs = {'from_date': kwargs['from_date'], 'to_date': kwargs['to_date']}

        if 'options' in kwargs:
            results_kwargs['options'] = kwargs['options']

        return HttpResponseRedirect(reverse_lazy('webinterface:results', kwargs=results_kwargs))

    def get(self, request, *args, **kwargs):
        from_date = datetime.datetime.strptime(kwargs['from_date'], '%d-%m-%Y').date()
        to_date = datetime.datetime.strptime(kwargs['to_date'], '%d-%m-%Y').date()

        context = dict()
        context['assignments_by_schedule'] = list()
        for schedule in Schedule.objects.enabled():
            context['assignments_by_schedule'].append(
                schedule.assignment_set.filter(cleaning_day__date__range=(from_date, to_date)))
        return self.render_to_response(context)


