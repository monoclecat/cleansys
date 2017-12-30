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
import timeit
from operator import itemgetter
import logging, math


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm

    def get_context_data(self, **kwargs):
        keywords = super(ConfigView, self).get_context_data(**kwargs)
        keywords['schedule_list'] = CleaningSchedule.objects.filter(deactivated=False)
        keywords['deactivated_schedule_list'] = CleaningSchedule.objects.filter(deactivated=True)
        keywords['cleaner_list'] = Cleaner.objects.filter(deactivated=False,
                                                          moved_out__gte=datetime.datetime.now().date())
        keywords['deactivated_cleaner_list'] = Cleaner.objects.exclude(deactivated=False,
                                                                       moved_out__gte=datetime.datetime.now().date())
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

            results_kwargs = {'from_day': start_date_raw[0], 'from_month': start_date_raw[1],
                              'from_year': start_date_raw[2], 'to_day': end_date_raw[0],
                              'to_month': end_date_raw[1], 'to_year': end_date_raw[2]}

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
        for schedule in CleaningSchedule.objects.filter(deactivated=False).order_by('cleaners_per_date'):
            schedule.new_cleaning_duties(
                datetime.date(int(kwargs['from_year']), int(kwargs['from_month']), int(kwargs['from_day'])),
                datetime.date(int(kwargs['to_year']), int(kwargs['to_month']), int(kwargs['to_day'])),
                clear_existing)
        time_end = timeit.default_timer()
        logging.getLogger(__name__).info("Assigning cleaning schedules took {}s".format(round(time_end-time_start, 2)))

        results_kwargs = {'from_day': kwargs['from_day'], 'from_month': kwargs['from_month'],
                                     'from_year': kwargs['from_year'], 'to_day': kwargs['to_day'],
                                     'to_month': kwargs['to_month'], 'to_year': kwargs['to_year']}

        if 'options' in kwargs:
            results_kwargs['options'] = kwargs['options']

        return HttpResponseRedirect(
            reverse_lazy('webinterface:results', kwargs=results_kwargs))

    def get(self, request, *args, **kwargs):
        from_date_raw = datetime.date(int(kwargs['from_year']), int(kwargs['from_month']), int(kwargs['from_day']))
        to_date_raw = datetime.date(int(kwargs['to_year']), int(kwargs['to_month']), int(kwargs['to_day']))

        kwargs['from_date'], kwargs['to_date'] = correct_dates_to_weekday([from_date_raw, to_date_raw], 6)

        if from_date_raw.weekday() != 6 or to_date_raw.weekday() != 6:
            results_kwargs = {'from_day': kwargs['from_date'].day, 'from_month': kwargs['from_date'].month,
                              'from_year': kwargs['from_date'].year, 'to_day': kwargs['to_date'].day,
                              'to_month': kwargs['to_date'].month, 'to_year': kwargs['to_date'].year}
            if 'options' in kwargs:
                results_kwargs['options'] = kwargs['options']
            return redirect(
                reverse_lazy('webinterface:results', kwargs=results_kwargs))

        if kwargs['to_date'] < kwargs['from_date']:
            temp_date = kwargs['from_date']
            kwargs['from_date'] = kwargs['to_date']
            kwargs['to_date'] = temp_date
        context = self.get_context_data(**kwargs)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        keywords = super(ResultsView, self).get_context_data(**kwargs)
        keywords['table_header'] = CleaningSchedule.objects.filter(deactivated=False).order_by('frequency')

        keywords['dates'] = []
        date_iterator = kwargs['from_date']
        one_week = datetime.timedelta(days=7)
        while date_iterator <= kwargs['to_date']:
            keywords['dates'].append(date_iterator)
            date_iterator += one_week

        relevant_cleaners = Cleaner.objects.filter(moved_in__lt=kwargs['to_date'], moved_out__gt=kwargs['from_date'])
        moved_in_during_timeframe = sorted(relevant_cleaners.filter(
            moved_in__gte=kwargs['from_date']).values('pk', 'moved_in'), key=itemgetter('moved_in'))

        moved_out_during_timeframe = sorted(relevant_cleaners.filter(
            moved_out__lte=kwargs['to_date']).values('pk', 'moved_out'), key=itemgetter('moved_out'))

        move_ins_and_move_outs = []
        for move_in_event in moved_in_during_timeframe:
            if move_ins_and_move_outs:
                if correct_dates_to_weekday(move_in_event['moved_in'], 6) == move_ins_and_move_outs[-1]['start_date']:
                    move_ins_and_move_outs[-1]['moved_in'].append(Cleaner.objects.get(pk=move_in_event['pk']))
                    continue
            move_ins_and_move_outs.append({'start_date': correct_dates_to_weekday(move_in_event['moved_in'], 6),
                                           'moved_in': [Cleaner.objects.get(pk=move_in_event['pk'])], 'moved_out': []})

        for move_out_event in moved_out_during_timeframe:
            for move_in_event in move_ins_and_move_outs:
                if correct_dates_to_weekday(move_out_event['moved_out'], 6) == \
                        move_in_event['start_date']:  # Here moved_out is a date
                    move_in_event['moved_out'].append(Cleaner.objects.get(pk=move_out_event['pk']))
                    break
            else:
                move_ins_and_move_outs.append({'start_date': correct_dates_to_weekday(move_out_event['moved_out'], 6),
                                               'moved_in': [],
                                               'moved_out': [Cleaner.objects.get(pk=move_out_event['pk'])]})

        move_ins_and_move_outs = sorted(move_ins_and_move_outs, key=itemgetter('start_date'))

        keywords['results'] = []
        if kwargs['from_date'] != move_ins_and_move_outs[0]['start_date']:
            keywords['results'].append({'start_date': kwargs['from_date'],
                                        'end_date': move_ins_and_move_outs[0]['start_date']-one_week,
                                        'moved_in': [], 'moved_out': []})

        miamo_iterator = 1
        if move_ins_and_move_outs:
            while miamo_iterator < len(move_ins_and_move_outs):
                move_ins_and_move_outs[miamo_iterator-1]['end_date'] = \
                    move_ins_and_move_outs[miamo_iterator]['start_date']-one_week
                miamo_iterator += 1
        move_ins_and_move_outs[-1]['end_date'] = kwargs['to_date']

        keywords['results'] += move_ins_and_move_outs

        for time_frame in keywords['results']:
            date_iterator = time_frame['start_date']
            time_frame['duties'] = []
            while date_iterator <= time_frame['end_date']:
                duties_on_date = [date_iterator]
                schedules = []
                for schedule in keywords['table_header']:
                    if schedule.defined_on_date(date_iterator):
                        duty = schedule.duties.filter(date=date_iterator)
                        if duty.exists():
                            duty = duty.first()
                            cleaners_for_duty = []
                            for cleaner in duty.cleaners.all():
                                cleaners_for_duty.append(cleaner.name)
                            schedules.append(cleaners_for_duty)
                        else:
                            schedules.append("")
                    else:
                        schedules.append(".")
                    duties_on_date.append(schedules)
                time_frame['duties'].append(duties_on_date)
                date_iterator += one_week

        if 'options' in kwargs and kwargs['options'] == 'stats':
            for time_frame in keywords['results']:
                time_frame['duty_counter'] = []
                time_frame['deviations_by_schedule'] = []
                for schedule in keywords['table_header']:
                    duties_in_timeframe = schedule.duties.filter(
                        date__range=(time_frame['start_date'], time_frame['end_date']))

                    element = [schedule.name, 0, 0, []]

                    deviation_of = []
                    sum_deviation_values = 0
                    ratios = schedule.deployment_ratios(for_date=time_frame['end_date'])
                    if ratios:
                        for cleaner, ratio in ratios:
                            element[3].append([cleaner.name, duties_in_timeframe.filter(cleaners=cleaner).count()])

                            deviation_of.append([cleaner, round(abs(1 - ratio), 3)])
                            sum_deviation_values += abs(1 - ratio)

                        element[3] = sorted(element[3], key=itemgetter(1), reverse=True)
                        element[1] = element[3][0][1]
                        element[2] = element[3][-1][1]
                        time_frame['duty_counter'].append(element)

                        schedule_data = [[schedule.name, round(sum_deviation_values/len(deviation_of), 3)]]
                        schedule_data.append(sorted(deviation_of, key=itemgetter(1), reverse=True))
                        time_frame['deviations_by_schedule'].append(schedule_data)
        return keywords


def update_schedules_for_cleaner(cleaner, new_associations):
    """new_associations takes a list or Queryset of schedules cleaner should now be assigned to.
    This function removes the cleaner from schedules he is not associated to anymore and adds him
    to schedules he wasn't associated with before."""
    prev_associations = CleaningSchedule.objects.filter(cleaners=cleaner, deactivated=False)
    for schedule in prev_associations:
        if schedule not in new_associations:
            schedule.cleaners.remove(cleaner)
    for schedule in new_associations:
        if schedule not in prev_associations:
            schedule.cleaners.add(cleaner)


class CleanersNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_new.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_schedules = form.cleaned_data['schedules']
        update_schedules_for_cleaner(self.object, curr_schedules)
        return HttpResponseRedirect(self.get_success_url())


class CleanersUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_edit.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_schedules = form.cleaned_data['schedules']
        update_schedules_for_cleaner(self.object, curr_schedules)
        return HttpResponseRedirect(self.get_success_url())


class CleanersDeactivateView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_deactivate.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.deactivated = True
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


# class CleaningScheduleReactivateView(DeleteView):
#     model = CleaningSchedule
#     success_url = reverse_lazy('webinterface:config')
#     template_name = 'webinterface/cleaning_schedule_reactivate.html'
#
#     def post(self, request, *args, **kwargs):
#         self.object = self.get_object()
#         self.object.deactivated = False
#         self.object.save()
#         return HttpResponseRedirect(self.get_success_url())


class CleaningScheduleNewView(CreateView):
    form_class = CleaningScheduleNewForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaning_schedule_new.html'


class CleaningScheduleDeactivateView(DeleteView):
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaning_schedule_deactivate.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.deactivated = True
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


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
