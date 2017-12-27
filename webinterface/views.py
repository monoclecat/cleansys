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
import logging


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"


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

            results_kwargs = {'from_day': start_date_raw[0], 'from_month': start_date_raw[1],
                              'from_year': start_date_raw[2], 'to_day': end_date_raw[0],
                              'to_month': end_date_raw[1], 'to_year': end_date_raw[2]}

            if 'show_deviations' in request.POST:
                results_kwargs['options'] = 'deviations'
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
        for schedule in CleaningSchedule.objects.all().order_by('cleaners_per_date'):
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
        keywords['table_header'] = CleaningSchedule.objects.all()

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

        if 'options' in kwargs and kwargs['options'] == 'deviations':
            keywords['deviations_by_schedule'] = []
            for schedule in keywords['table_header']:
                logging.debug("------------- CALCULATING DEVIATION FOR {} -------------".format(schedule.name))
                schedule_data = [schedule.name]

                sum_of_ratios = {}
                date_iterator = kwargs['from_date']
                divider = 0
                while date_iterator <= kwargs['to_date']:
                    ratios = schedule.deployment_ratios(date_iterator)
                    logging_text = "Ratios on {}: ".format(date_iterator)
                    for cleaner, ratio in ratios:
                        logging_text += "{}:{}".format(cleaner.name, round(ratio, 3)) + "  "
                        if cleaner not in sum_of_ratios:
                            sum_of_ratios[cleaner] = abs(1 - ratio)
                        else:
                            sum_of_ratios[cleaner] += abs(1 - ratio)
                    logging.debug(logging_text)
                    divider += 1
                    date_iterator += one_week
                for key in sum_of_ratios:
                    sum_of_ratios[key] /= divider
                    sum_of_ratios[key] = round(sum_of_ratios[key], 4)
                schedule_data.append(sum_of_ratios)
                keywords['deviations_by_schedule'].append(schedule_data)
                logging.debug("")

            keywords['deviations_by_cleaner'] = {}
            for schedule, deviations in keywords['deviations_by_schedule']:
                for key in deviations:
                    divider = CleaningSchedule.objects.filter(cleaners=key).count()
                    if key not in keywords['deviations_by_cleaner']:
                        keywords['deviations_by_cleaner'][key] = deviations[key]/divider
                    else:
                        keywords['deviations_by_cleaner'][key] += deviations[key]/divider

            keywords['complete_deviation'] = 0
            for key in keywords['deviations_by_cleaner']:
                keywords['complete_deviation'] += keywords['deviations_by_cleaner'][key]
                keywords['deviations_by_cleaner'][key] = round(keywords['deviations_by_cleaner'][key], 4)
            if keywords['deviations_by_cleaner']:
                keywords['complete_deviation'] /= len(keywords['deviations_by_cleaner'])
                keywords['complete_deviation'] = round(keywords['complete_deviation'], 4)

            # for time_frame in keywords['results']:
            #     time_frame['statistics'] = []
            #     for schedule in CleaningSchedule.objects.all():
            #
            #         duties_in_timeframe = schedule.duties.filter(
            #             date__range=(time_frame['start_date'], time_frame['end_date']))
            #         relevant_cleaners = schedule.cleaners.filter(
            #             moved_in__lte=time_frame['end_date'], moved_out__gte=time_frame['start_date'])
            #         max_cleaning_duties = math.ceil(duties_in_timeframe.count() *
            #                                         schedule.cleaners_per_date / relevant_cleaners.count())
            #
            #         element = [schedule.name, max_cleaning_duties, []]
            #         for cleaner_pk, ratio in schedule.deployment_ratios(for_date=time_frame['end_date']):
            #             element[2].append([Cleaner.objects.get(pk=cleaner_pk).name, round(ratio, 2),
            #                                duties_in_timeframe.filter(cleaners=Cleaner.objects.get(pk=cleaner_pk)).count()])
            #         element[2] = sorted(element[2], key=itemgetter(2))
            #         time_frame['statistics'].append(element)

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
