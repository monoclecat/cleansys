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

class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm
    success_url = "/results/1-1-1111/1-1-1112"

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

            if end_date > start_date:
                date_iterator = start_date
                to_add = datetime.timedelta(days=7)
                while date_iterator <= end_date:
                    for job in CleaningSchedule.objects.all():
                        if not CleaningDuty.objects.filter(date=date_iterator, schedule__name=job.name).exists():
                            # 2: Even weeks 3: Odd weeks
                            if job.frequency == 1 or \
                                    job.frequency == 2 and date_iterator.isocalendar()[1] % 2 == 0 or \
                                    job.frequency == 3 and date_iterator.isocalendar()[1] % 2 == 1:

                                CleaningDuty.objects.create(schedule=job, date=date_iterator)
                    date_iterator += to_add

                duties = CleaningDuty.objects.filter(
                    date__range=(start_date, end_date))

                distribution_structure = []
                for schedule in CleaningSchedule.objects.all().order_by('-frequency'):
                    cleaners_for_schedule = Cleaner.objects.filter(assigned_to__name=schedule.name)
                    cleaners_with_data = []
                    for cleaner in cleaners_for_schedule:
                        cleaners_with_data.append([cleaner, 0])
                    distribution_structure.append(
                        [duties.filter(schedule__name=schedule.name), cleaners_with_data])





                # distribution_structure ==
                # [
                #   for every schedule:
                #   [
                #       <list of all CleaningDuties in time frame>,
                #       [list of [<cleaner assigned to this schedule>, <times he/she already cleaned this>]
                #   ], ...
                # ]



                # duty.cleaners.add(Cleaner.objects.first())

                return self.form_valid(form)
        return self.form_invalid(form)



class ResultsView(TemplateView):
    template_name = 'webinterface/results.html'

    def get(self, request, *args, **kwargs):
        kwargs['from_date'] = datetime.date(int(kwargs['from_year']), int(kwargs['from_month']), int(kwargs['from_day']))
        kwargs['to_date'] = datetime.date(int(kwargs['to_year']), int(kwargs['to_month']), int(kwargs['to_day']))
        context = self.get_context_data(**kwargs)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        keywords = super(ResultsView, self).get_context_data(**kwargs)
        keywords['object_list'] = CleaningDuty.objects.filter(date__range=(kwargs['from_date'], kwargs['to_date']))
        return keywords


class CleanersView(ListView):
    model = Cleaner
    template_name = 'webinterface/cleaner.html'


class CleanersNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:cleaners')
    template_name = 'webinterface/cleaner_new.html'


class CleanersDeleteView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:cleaners')
    template_name = 'webinterface/cleaner_delete.html'


class CleanersUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:cleaners')
    template_name = 'webinterface/cleaner_edit.html'


class CleaningScheduleView(ListView):
    model = CleaningSchedule
    template_name = 'webinterface/cleaning_schedule.html'


class CleaningScheduleNewView(CreateView):
    form_class = CleaningScheduleForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:cleaning-schedule')
    template_name = 'webinterface/cleaning_schedule_new.html'


class CleaningScheduleDeleteView(DeleteView):
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:cleaning-schedule')
    template_name = 'webinterface/cleaning_schedule_delete.html'


class CleaningScheduleUpdateView(UpdateView):
    form_class = CleaningScheduleForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:cleaning-schedule')
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
