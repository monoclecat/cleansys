from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.views.generic.edit import FormView, CreateView, DeleteView, UpdateView

from .forms import *
from .models import *

import datetime
import timeit
from operator import itemgetter
import logging


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"

    def get_context_data(self, **kwargs):
        keywords = super(WelcomeView, self).get_context_data(**kwargs)
        keywords['cleaner_list'] = Cleaner.objects.filter(moved_out__gte=datetime.datetime.now().date())

        return keywords


class DutySwitchView(TemplateView):
    template_name = "webinterface/switch_duty.html"

    def get_context_data(self, **kwargs):
        keywords = super(DutySwitchView, self).get_context_data(**kwargs)
        duty = CleaningDuty.objects.get(pk=kwargs['duty_pk'])
        schedule = duty.cleaningschedule_set.first()

        if duty.date <= datetime.datetime.now().date() + datetime.timedelta(days=20):
            keywords['short_notice_flag'] = True

        ratios = schedule.deployment_ratios(duty.date)
        logging.debug("------------ Looking for replacement cleaners -----------")
        replacement_cleaners = []
        for cleaner, ratio in ratios:
            logging.debug("{}:   Not in duty:{} Free:{} Willing:{}".format(cleaner.name, cleaner not in duty.cleaners.all(),
                                                                 cleaner.free_on_date(duty.date), cleaner.willing_to_switch))
            if cleaner not in duty.cleaners.all() and cleaner.free_on_date(duty.date) and cleaner.willing_to_switch:
                replacement_cleaners.append(cleaner)
            if len(replacement_cleaners) == 3:
                break
        else:
            logging.debug("We need to select cleaners that are not free today.")
            if len(replacement_cleaners) == 0:
                keywords['double_duty_flag'] = True
                for cleaner, ratio in ratios:
                    logging.debug("{}:   Not in duty:{} Duties today:{} Willing:{}".format(cleaner.name, cleaner not in duty.cleaners.all(),
                                                                         cleaner.cleaningduty_set.filter(
                                                                             date=duty.date).count(),
                                                                         cleaner.willing_to_switch))
                    if cleaner not in duty.cleaners.all() and \
                            cleaner.cleaningduty_set.filter(date=duty.date).count() <= 2 and cleaner.willing_to_switch:
                        replacement_cleaners.append(cleaner)
                    if len(replacement_cleaners) == 3:
                        break

        logging.debug("Replacement cleaners: {}".format(replacement_cleaners))
        replacement_duties = []
        for cleaner in replacement_cleaners:
            duties = schedule.duties.filter(cleaners=cleaner, date__gt=duty.date).order_by('date')
            if duties.count() >= 2:
                duties = duties[:2]
            for repl_duty in duties:
                replacement_duties.append([cleaner, repl_duty])

        keywords['duty'] = duty
        keywords['replacement_duties'] = replacement_duties
        keywords['old_cleaner'] = Cleaner.objects.get(pk=kwargs['old_cleaner_pk'])
        keywords['schedule'] = schedule

        return keywords

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        old_cleaner = Cleaner.objects.get(pk=request.POST['old_cleaner_pk'])
        duty_for_replacing_cleaner = CleaningDuty.objects.get(pk=request.POST['duty_pk'])

        if 'short_notice_call' not in request.POST:
            for key, val in request.POST.items():
                banana_split = key.split("-")
                if banana_split[0] == 'option':
                    replacing_cleaner = Cleaner.objects.get(pk=banana_split[1])
                    new_duty_for_old_cleaner = CleaningDuty.objects.get(pk=banana_split[2])
                    break
            else:
                logging.warning("Post request tried without valid data!")
                return HttpResponseRedirect(reverse_lazy(
                    'webinterface:welcome'))

            duty_for_replacing_cleaner.excluded.add(old_cleaner)
            duty_for_replacing_cleaner.cleaners.remove(old_cleaner)
            duty_for_replacing_cleaner.cleaners.add(replacing_cleaner)

            new_duty_for_old_cleaner.cleaners.remove(replacing_cleaner)
            new_duty_for_old_cleaner.cleaners.add(old_cleaner)

            # TODO notify replacement cleaner and update calendars
        else:
            logging.debug("!!!!!!!!Short notice request sent!!!!!!!!!!")
            pass
            # TODO send Slack messages to other cleaners
            # TODO when someone agrees, send message to request sender

        return HttpResponseRedirect(reverse_lazy(
            'webinterface:cleaner-duties-page1', kwargs={'pk': old_cleaner.pk, 'slug': "wrong_slug"}))


class CleaningDutyView(TemplateView):
    template_name = "webinterface/cleaning_duties.html"

    def get(self, request, *args, **kwargs):
        cleaner = Cleaner.objects.get(pk=kwargs['pk'])

        if 'page' not in kwargs or int(kwargs['page']) <= 0:
            return redirect(
                reverse_lazy('webinterface:cleaner-duties',
                             kwargs={'pk': kwargs['pk'], 'slug': slugify(cleaner.name), 'page': 1}))

        if 'slug' not in kwargs or kwargs['slug'] != slugify(cleaner.name):
            return redirect(
                reverse_lazy('webinterface:cleaner-duties',
                             kwargs={'pk': kwargs['pk'], 'slug': slugify(cleaner.name), 'page': kwargs['page']}))

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        keywords = super(CleaningDutyView, self).get_context_data(**kwargs)
        pagination = 25

        keywords['table_header'] = CleaningSchedule.objects.all().order_by('frequency')
        keywords['cleaner'] = Cleaner.objects.get(pk=keywords['pk'])

        page = int(keywords['page'])

        duties = CleaningDuty.objects.filter(cleaners=keywords['cleaner'],
                                             date__gte=datetime.datetime.now().date() - datetime.timedelta(days=3)
                                             ).order_by('date')

        if pagination*page <= duties.count():
            duties = duties[pagination*(page-1):pagination*page]
        elif pagination*(page-1) < duties.count() <= pagination*page:
            duties = duties[pagination*(page-1):]
        else:
            duties = []

        keywords['duties_due_now'] = []

        keywords['duties'] = []

        for duty in duties:
            schedule = CleaningSchedule.objects.get(duties=duty)
            other_cleaners_for_duty = []
            for cleaner in duty.cleaners.all():
                if cleaner != keywords['cleaner']:
                    other_cleaners_for_duty.append(cleaner)
            if duty.date == correct_dates_to_weekday(datetime.datetime.now().date(), 6):
                keywords['duties_due_now'].append([duty.date, schedule, other_cleaners_for_duty, duty.pk])
            else:
                keywords['duties'].append([duty.date, schedule, other_cleaners_for_duty, duty.pk])

        return keywords


class CleaningDutyAllView(TemplateView):
    template_name = "webinterface/cleaning_duties_all.html"

    def get_context_data(self, **kwargs):
        keywords = super(CleaningDutyAllView, self).get_context_data(**kwargs)
        pagination = 25
        if 'pk' in keywords:
            keywords['cleaner'] = Cleaner.objects.get(pk=keywords['pk'])

        if 'page' not in keywords:
            keywords['page'] = 1

        page = int(keywords['page'])

        keywords['table_header'] = CleaningSchedule.objects.all().order_by('frequency')
        keywords['cleaners'] = Cleaner.objects.all()

        one_week = datetime.timedelta(days=7)
        date_iterator = datetime.datetime.now().date() + one_week * pagination * (page-1)

        keywords['duties'] = []

        while date_iterator < datetime.datetime.now().date() + one_week * pagination * page:
            duties_on_date = [date_iterator]
            schedules = []
            for schedule in keywords['table_header']:
                if schedule.defined_on_date(date_iterator):
                    duty = schedule.duties.filter(date=date_iterator)
                    if duty.exists():
                        duty = duty.first()
                        cleaners_for_duty = []
                        for cleaner in duty.cleaners.all():
                            cleaners_for_duty.append(cleaner)
                        schedules.append(cleaners_for_duty)
                    else:
                        schedules.append("")
                else:
                    schedules.append(".")
                duties_on_date.append(schedules)
            keywords['duties'].append(duties_on_date)
            date_iterator += one_week

        return keywords


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm

    def get_context_data(self, **kwargs):
        keywords = super(ConfigView, self).get_context_data(**kwargs)
        keywords['schedule_list'] = CleaningSchedule.objects.all()
        all_active_cleaners = Cleaner.objects.filter(moved_out__gte=datetime.datetime.now().date())
        keywords['cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=False)
        keywords['no_slack_cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=True)
        keywords['deactivated_cleaner_list'] = Cleaner.objects.exclude(moved_out__gte=datetime.datetime.now().date())
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
        keywords['table_header'] = CleaningSchedule.objects.all().order_by('frequency')

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


def update_groups_for_cleaner(cleaner, new_association):
    """new_associations takes a list or Queryset of schedules cleaner should now be assigned to.
    This function removes the cleaner from schedules he is not associated to anymore and adds him
    to schedules he wasn't associated with before."""
    prev_association = CleaningScheduleGroup.objects.get(cleaners=cleaner)
    if prev_association != new_association:
        prev_association.cleaners.remove(cleaner)
        new_association.cleaners.add(cleaner)


class CleanerNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_new.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_groups = form.cleaned_data['schedule_groups']
        update_groups_for_cleaner(self.object, curr_groups)
        return HttpResponseRedirect(self.get_success_url())


class CleanerUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_edit.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_groups = form.cleaned_data['schedule_group']
        update_groups_for_cleaner(self.object, curr_groups)
        return HttpResponseRedirect(self.get_success_url())


class CleanerDeleteView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/cleaner_delete.html'


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
