from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import FormView, CreateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import *
from .forms import *

import datetime
from copy import deepcopy
from operator import itemgetter
import random, math


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"


def correct_date_to_weekday(days, weekday):
    """Days is a list of datetime.date objects you want converted. 0 = Monday, 6 = Sunday"""
    corrected_days = []
    for day in days:
        day += datetime.timedelta(days=weekday - day.weekday())
        corrected_days.append(day)
    return corrected_days


def create_distribution_structure(start_date, end_date):
    """Used to assign cleaners to their cleaning duties in the time frame.
    Creates copies of all Schedules and Cleaners involved.
    distribution_structure ==
    [
        for every schedule:
        [
            <schedule object>
            [list of all CleaningDuties in time frame],
            [list of [<cleaner assigned to this schedule>, <times he/she already cleaned this>] ]
        ], ...
    ]
    """
    duties = CleaningDuty.objects.filter(date__range=(start_date, end_date))

    schedule_templates = CleaningSchedule.objects.all().filter(template=True).order_by('-frequency')
    schedule_copies = []
    for schedule in schedule_templates:
        schedule_copies.append(schedule.copy())

    cleaner_templates = Cleaner.objects.filter(template=True)
    cleaner_copies = []
    for cleaner in cleaner_templates:
        cleaner_copies.append(cleaner.copy())

    distribution_structure = []
    for schedule in schedule_copies:
        cleaners_with_data = []
        for cleaner in cleaner_copies:
            if schedule in cleaner.assigned_to:
                cleaners_with_data.append([cleaner, 0])
        distribution_structure.append(
            [schedule, duties.filter(schedule__id=schedule.id), cleaners_with_data])

    for schedule in distribution_structure:
        for cleaner in schedule[2]:
            cleaner[1] = duties.filter(schedule__id=schedule[0].id, cleaners=cleaner[0]).count()

    return distribution_structure


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm

    def get_context_data(self, **kwargs):
        keywords = super(ConfigView, self).get_context_data(**kwargs)
        keywords['schedule_list'] = CleaningSchedule.objects.all()
        keywords['cleaner_list'] = Cleaner.objects.all()
        return keywords

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()

        if form.is_valid():
            start_date_raw = request.POST['start_date'].split(".")
            end_date_raw = request.POST['end_date'].split(".")
            start_date = datetime.date(int(start_date_raw[2]), int(start_date_raw[1]), int(start_date_raw[0]))
            end_date = datetime.date(int(end_date_raw[2]), int(end_date_raw[1]), int(end_date_raw[0]))

            start_date, end_date = correct_date_to_weekday([start_date, end_date], 6)

            if end_date > start_date:
                date_iterator = start_date
                to_add = datetime.timedelta(days=7)
                while date_iterator <= end_date:
                    for schedule in CleaningSchedule.objects.all():
                        schedule.new_cleaning_duty(date_iterator)
                    date_iterator += to_add

                return HttpResponseRedirect(
                    reverse_lazy('webinterface:results',
                                 kwargs={'from_day': start_date_raw[0], 'from_month': start_date_raw[1],
                                         'from_year': start_date_raw[2], 'to_day': end_date_raw[0],
                                         'to_month': end_date_raw[1], 'to_year': end_date_raw[2]}))
        return self.form_invalid(form)


class ResultsView(TemplateView):
    template_name = 'webinterface/results.html'

    def get(self, request, *args, **kwargs):
        from_date_raw = datetime.date(int(kwargs['from_year']), int(kwargs['from_month']), int(kwargs['from_day']))
        to_date_raw = datetime.date(int(kwargs['to_year']), int(kwargs['to_month']), int(kwargs['to_day']))

        kwargs['from_date'], kwargs['to_date'] = correct_date_to_weekday([from_date_raw, to_date_raw], 6)

        if from_date_raw.weekday() != 6 or to_date_raw.weekday() != 6:
            return redirect(
                reverse_lazy('webinterface:results',
                         kwargs={'from_day': kwargs['from_date'].day, 'from_month': kwargs['from_date'].month,
                                 'from_year': kwargs['from_date'].year, 'to_day': kwargs['to_date'].day,
                                 'to_month': kwargs['to_date'].month, 'to_year': kwargs['to_date'].year}))

        if kwargs['to_date'] < kwargs['from_date']:
            temp_date = kwargs['from_date']
            kwargs['from_date'] = kwargs['to_date']
            kwargs['to_date'] = temp_date
        context = self.get_context_data(**kwargs)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        keywords = super(ResultsView, self).get_context_data(**kwargs)
        keywords['table_header'] = CleaningSchedule.objects.all()

        keywords['dates'] = []
        date_iterator = kwargs['from_date']
        to_add = datetime.timedelta(days=7)
        while date_iterator <= kwargs['to_date']:
            keywords['dates'].append(date_iterator)
            date_iterator += to_add

        keywords['duties'] = []
        for date in keywords['dates']:
            duties_on_date = [date]
            schedules = []
            for schedule in keywords['table_header']:
                duty = schedule.duties.filter(date=date)
                if duty.exists():
                    schedules.append(duty.first())
                else:
                    schedules.append("")
                duties_on_date.append(schedules)
            keywords['duties'].append(duties_on_date)

        keywords['statistics'] = []
        for schedule in CleaningSchedule.objects.all():
            element = [schedule.name, round(schedule.max_cleaning_ratio(kwargs['to_date']), 2), []]
            for cleaner_pk, ratio in schedule.deployment_ratios(kwargs['to_date']):
                element[2].append([Cleaner.objects.get(pk=cleaner_pk).name, round(ratio, 2)])

            keywords['statistics'].append(element)
        return keywords


class CleanersNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_new.html'


class CleanersDeleteView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_delete.html'


class CleanersUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_edit.html'


class CleaningScheduleNewView(CreateView):
    form_class = CleaningScheduleForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaning_schedule_new.html'


class CleaningScheduleDeleteView(DeleteView):
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaning_schedule_delete.html'


class CleaningScheduleUpdateView(UpdateView):
    form_class = CleaningScheduleForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaning_schedule_edit.html'


def login_view(request):
    if request.method == 'POST' and 'login' in request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
        return HttpResponseRedirect(request.POST['next'])
    elif request.method == 'POST' and 'logout' in request.POST:
        logout(request)
        return HttpResponseRedirect(request.POST['next'])
    else:
        return render(request, 'webinterface/login.html', {'next': request.GET.get('next', '/login/')})
