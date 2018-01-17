from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.core.paginator import Paginator
from django.views.generic.edit import FormView, CreateView, DeleteView, UpdateView
from django.core.exceptions import SuspiciousOperation
from django.http import Http404
from django.core.paginator import *


from .forms import *
from .models import *

import datetime
import timeit
from operator import itemgetter
import logging


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"

    def get_context_data(self, **kwargs):
        context = super(WelcomeView, self).get_context_data(**kwargs)
        context['cleaner_list'] = Cleaner.objects.filter(moved_out__gte=datetime.date.today())
        context['schedule_list'] = CleaningSchedule.objects.all()

        return context


class DutyCleanView(TemplateView):
    template_name = "webinterface/clean_duty.html"

    def get_context_data(self, **kwargs):
        context = super(DutyCleanView, self).get_context_data(**kwargs)
        try:
            context['duty'] = Duty.objects.get(pk=kwargs['duty_pk'])
            context['cleaner'] = Cleaner.objects.get(pk=kwargs['cleaner_pk'])

            other_cleaners_for_duty = []
            for cleaner in context['duty'].cleaners.all():
                if cleaner != context['cleaner']:
                    other_cleaners_for_duty.append(cleaner)
            context['other_cleaners'] = other_cleaners_for_duty

            context['schedule'] = context['duty'].cleaningschedule_set.first()
            context['task_cleaner_pairs'] = context['duty'].get_tasks()

        except (Duty.DoesNotExist, Cleaner.DoesNotExist):
            Http404("Dieser Putzdienst oder dieser Putzer existieren nicht.")

        return context

    def post(self, request, *args, **kwargs):
        if 'cleaned' in request.POST and request.POST['cleaned']:
            try:
                cleaner = Cleaner.objects.get(pk=kwargs['cleaner_pk'])
                duty = Duty.objects.get(pk=kwargs['duty_pk'])
                if not duty.task_completed(request.POST['cleaned'], cleaner):
                    raise SuspiciousOperation("Task name not in tasks or cleaner not in assigned cleaners for date.")
                duty.save()

                return HttpResponseRedirect(reverse_lazy(
                    'webinterface:clean-duty',
                    kwargs={'cleaner_pk': cleaner.pk, 'duty_pk': duty.pk}))
            except (Cleaner.DoesNotExist, Duty.DoesNotExist):
                raise SuspiciousOperation("Cleaner or Duty does not exist.")


class DutySwitchView(TemplateView):
    template_name = "webinterface/switch_duty.html"

    def get_context_data(self, **kwargs):
        context = super(DutySwitchView, self).get_context_data(**kwargs)
        try:
            duty_switch = DutySwitch.objects.get(pk=kwargs['pk'])

            context['duty_switch'] = duty_switch
            context['replacement_duties'] = duty_switch.get_destinations()
            context['perspective'] = 'selected' if 'answer' in kwargs else 'source'

        except DutySwitch.DoesNotExist:
            Http404("Diese Putzdienst-Tausch-Seite existiert nicht.")

        return context

    def post(self, request, *args, **kwargs):
        duty_switch = None
        try:
            duty_switch = DutySwitch.objects.get(pk=kwargs['pk'])
        except DutySwitch.DoesNotExist:
            Http404("Diese Putzdienst-Tausch-Seite existiert nicht.")

        try:
            redirect_cleaner_pk = Cleaner.objects.get(pk=request.POST['redirect_cleaner_pk'])
        except Cleaner.DoesNotExist:
            raise SuspiciousOperation("Invalid PK")

        if 'delete' in request.POST:
            duty_switch.delete()
        elif 'accept' in request.POST:
            duty_switch.selected_was_accepted()
        elif 'reject' in request.POST:
            duty_switch.selected_was_rejected()
            duty_switch.save()
        else:
            for key, val in request.POST.items():
                key_list = key.split("-")
                if key_list:
                    if key_list[0] == "select":
                        try:
                            duty_switch.set_selected(Cleaner.objects.get(pk=key_list[1]), Duty.objects.get(pk=key_list[2]))
                            duty_switch.save()
                        except (Cleaner.DoesNotExist, Duty.DoesNotExist):
                            raise SuspiciousOperation("Invalid PKs")

        return HttpResponseRedirect(reverse_lazy(
            'webinterface:cleaner-duties',
            kwargs={'slug': redirect_cleaner_pk.slug, 'page': 1}))


class CleanerView(TemplateView):
    template_name = "webinterface/cleaner.html"

    def post(self, request, *args, **kwargs):
        if 'switch' in request.POST:
            if 'source_duty_pk' in request.POST and request.POST['source_duty_pk']:
                try:
                    source_cleaner = Cleaner.objects.get(pk=kwargs['pk'])
                    source_duty = Duty.objects.get(pk=request.POST['source_duty_pk'])
                    duty_to_switch = DutySwitch.objects.create(source_cleaner=source_cleaner,
                                                               source_duty=source_duty)
                    return HttpResponseRedirect(reverse_lazy(
                        'webinterface:switch-duty', kwargs={'pk': duty_to_switch.pk}))
                except (Cleaner.DoesNotExist, Duty.DoesNotExist):
                    raise SuspiciousOperation("Invalid PKs")
            else:
                raise SuspiciousOperation("Invalid POST data sent by client")
        elif 'clean' in request.POST:
            if 'source_duty_pk' in request.POST and request.POST['source_duty_pk']:
                try:
                    duty_to_clean = Duty.objects.get(pk=request.POST['source_duty_pk'])
                    if duty_to_clean.tasks is None:
                        duty_to_clean.initiate_tasks()
                        duty_to_clean.save()

                    return HttpResponseRedirect(reverse_lazy(
                        'webinterface:clean-duty', kwargs={'duty_pk': duty_to_clean.pk, 'cleaner_pk': kwargs['pk']}))

                except Duty.DoesNotExist:
                    raise SuspiciousOperation("Invalid Duty PK")

        return HttpResponseRedirect(reverse_lazy(
            'webinterface:cleaner-duties',
            kwargs={'slug': kwargs['slug'], 'page': kwargs['page']}))

    def get(self, request, *args, **kwargs):
        try:
            cleaner = Cleaner.objects.get(slug=kwargs['slug'])
        except Cleaner.DoesNotExist:
            cleaner = None
            Http404("Putzer existiert nicht!")

        if 'page' not in kwargs or int(kwargs['page']) <= 0:
            return redirect(
                reverse_lazy('webinterface:cleaner-duties', kwargs={'slug': cleaner.slug, 'page': 1}))

        context = {}

        context['table_header'] = CleaningSchedule.objects.all().order_by('frequency')
        context['cleaner'] = cleaner

        start_date = correct_dates_to_weekday(datetime.date.today() - datetime.timedelta(days=3), 6)

        duties = Duty.objects.filter(cleaners=context['cleaner'],
                                             date__gte=start_date + datetime.timedelta(days=7))

        pagination = Paginator(duties, 25)
        context['page'] = pagination.get_page(kwargs['page'])

        context['duties_due_now'] = Duty.objects.filter(cleaners=context['cleaner'], date=start_date)

        return self.render_to_response(context)


class CleaningScheduleView(TemplateView):
    template_name = "webinterface/cleaning_schedule.html"

    def get(self, request, *args, **kwargs):
        context = {}

        if 'cleaner_slug' in kwargs and kwargs['cleaner_slug']:
            try:
                context['highlighted_cleaner'] = Cleaner.objects.get(slug=kwargs['cleaner_slug'])
            except Cleaner.DoesNotExist:
                Http404("Putzer existert nicht")

        try:
            context['schedule'] = CleaningSchedule.objects.get(slug=kwargs['slug'])
        except CleaningSchedule.DoesNotExist:
            Http404("Putzplan existiert nicht.")

        context['cleaners'] = Cleaner.objects.all()

        start_date = correct_dates_to_weekday(datetime.date.today() - datetime.timedelta(days=3), 6)

        duties = context['schedule'].duties.filter(date__gte=start_date)

        pagination = Paginator(duties, 25)
        context['page'] = pagination.get_page(kwargs['page'])

        return self.render_to_response(context)


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm

    def get_context_data(self, **kwargs):
        context = super(ConfigView, self).get_context_data(**kwargs)
        context['schedule_list'] = CleaningSchedule.objects.all()
        all_active_cleaners = Cleaner.objects.filter(moved_out__gte=datetime.date.today())
        context['cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=False)
        context['no_slack_cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=True)
        context['deactivated_cleaner_list'] = Cleaner.objects.exclude(moved_out__gte=datetime.date.today())
        context['schedule_group_list'] = CleaningScheduleGroup.objects.all()
        return context

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
        context = super(ResultsView, self).get_context_data(**kwargs)
        context['table_header'] = CleaningSchedule.objects.all().order_by('frequency')

        context['dates'] = []
        date_iterator = kwargs['from_date']
        one_week = datetime.timedelta(days=7)
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

        context['results'] = []
        if move_ins_and_move_outs:
            if kwargs['from_date'] != move_ins_and_move_outs[0]['start_date']:
                context['results'].append({'start_date': kwargs['from_date'],
                                            'end_date': move_ins_and_move_outs[0]['start_date']-one_week,
                                            'moved_in': [], 'moved_out': []})

            miamo_iterator = 1
            while miamo_iterator < len(move_ins_and_move_outs):
                move_ins_and_move_outs[miamo_iterator-1]['end_date'] = \
                    move_ins_and_move_outs[miamo_iterator]['start_date']-one_week
                miamo_iterator += 1
            move_ins_and_move_outs[-1]['end_date'] = kwargs['to_date']
        else:
            context['results'].append({'start_date': kwargs['from_date'],
                                        'end_date': kwargs['to_date'],
                                        'moved_in': [], 'moved_out': []})

        context['results'] += move_ins_and_move_outs

        for time_frame in context['results']:
            date_iterator = time_frame['start_date']
            time_frame['duties'] = []
            while date_iterator <= time_frame['end_date']:
                duties_on_date = [date_iterator]
                schedules = []
                for schedule in context['table_header']:
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
            for time_frame in context['results']:
                time_frame['duty_counter'] = []
                time_frame['deviations_by_schedule'] = []
                for schedule in context['table_header']:
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
        return context


def update_groups_for_cleaner(cleaner, new_association):
    """new_associations takes a list or Queryset of schedules cleaner should now be assigned to.
    This function removes the cleaner from schedules he is not associated to anymore and adds him
    to schedules he wasn't associated with before."""
    try:
        prev_association = CleaningScheduleGroup.objects.get(cleaners=cleaner)

        if prev_association != new_association:
            prev_association.cleaners.remove(cleaner)
            new_association.cleaners.add(cleaner)
    except CleaningScheduleGroup.DoesNotExist:
        new_association.cleaners.add(cleaner)


class CleanerNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_groups = form.cleaned_data['schedule_group']
        update_groups_for_cleaner(self.object, curr_groups)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Füge neuen Putzer hinzu"
        return context


class CleanerUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def form_valid(self, form):
        self.object = form.save()
        curr_groups = form.cleaned_data['schedule_group']
        update_groups_for_cleaner(self.object, curr_groups)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzerprofil"
        return context


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
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erzeuge neuen Putzplan"
        return context


class CleaningScheduleUpdateView(UpdateView):
    form_class = CleaningScheduleForm
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzplan"
        return context


class CleaningScheduleDeleteView(DeleteView):
    model = CleaningSchedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzplan"
        return context


class CleaningScheduleGroupNewView(CreateView):
    form_class = CleaningScheduleGroupForm
    model = CleaningScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erstelle eine neue Putzplan-Gruppierung"
        return context


class CleaningScheduleGroupUpdateView(UpdateView):
    form_class = CleaningScheduleGroupForm
    model = CleaningScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere eine Putzplan-Gruppierung"
        return context


class CleaningScheduleGroupDeleteView(DeleteView):
    form_class = CleaningScheduleGroupForm
    model = CleaningScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzplan-Gruppierung"
        return context


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
