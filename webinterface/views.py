from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin
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
        context['schedule_list'] = Schedule.objects.all()

        return context


class AssignmentView(UpdateView):
    template_name = "webinterface/clean_duty.html"
    model = Assignment
    form_class = AssignmentForm
    pk_url_kwarg = "assignment_pk"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(AssignmentView, self).get_context_data(**kwargs)

        try:
            context['tasks'] = self.object.schedule.cleaningday_set.get(date=self.object.date).tasks.all()
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
                    if task.cleaned_by == assignment.cleaner:
                        task.cleaned_by = None
                    else:
                        context = self.get_context_data(**kwargs)
                        context['already_cleaned_error'] = "{} wurde in der Zwischenzeit schon von {} gemacht!".format(
                            task.name, task.cleaned_by)
                        return self.render_to_response(context)
                else:
                    task.cleaned_by = assignment.cleaner
                task.save()
                return HttpResponseRedirect(self.get_success_url())

            except (Task.DoesNotExist, Assignment.DoesNotExist):
                raise SuspiciousOperation("Task or Assignment does not exist.")
        else:
            return super().post(args, kwargs)


class DutySwitchView(TemplateView):
    template_name = "webinterface/switch_duty.html"

    def get_context_data(self, **kwargs):
        context = super(DutySwitchView, self).get_context_data(**kwargs)
        try:
            duty_switch = DutySwitch.objects.get(pk=kwargs['pk'])

            context['duty_switch'] = duty_switch
            context['perspective'] = 'selected' if 'answer' in kwargs else 'source'

        except DutySwitch.DoesNotExist:
            Http404("Diese Putzdienst-Tausch-Seite existiert nicht.")

        return context

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

        return HttpResponseRedirect(reverse_lazy(
            'webinterface:cleaner-duties',
            kwargs={'slug': request.POST['redirect_cleaner_slug'], 'page': 1}))


class CleanerView(TemplateView):
    template_name = "webinterface/cleaner.html"

    def post(self, request, *args, **kwargs):
        if 'switch' in request.POST:
            if 'source_assignment_pk' in request.POST and request.POST['source_assignment_pk']:
                try:
                    source_assignment = Assignment.objects.get(pk=request.POST['source_assignment_pk'])
                    duty_to_switch = DutySwitch.objects.create(source_assignment=source_assignment)
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
                    schedule = assignment.schedule
                    try:
                        cleaning_day = schedule.cleaningday_set.get(date=assignment.date)
                    except CleaningDay.DoesNotExist:
                        cleaning_day = None
                        raise SuspiciousOperation("Invalid CleaningDay PK")

                    if not cleaning_day.tasks.all():
                        cleaning_day.initiate_tasks()
                        cleaning_day.save()

                    return HttpResponseRedirect(reverse_lazy(
                        'webinterface:clean-duty', kwargs={'assignment_pk': assignment.pk}))

                except Assignment.DoesNotExist:
                    raise SuspiciousOperation("Invalid Assignment PK")
        else:
            raise SuspiciousOperation("POST sent that didn't match a catchable case!")

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

        context['table_header'] = Schedule.objects.all().order_by('frequency')
        context['cleaner'] = cleaner

        start_date = correct_dates_to_weekday(datetime.date.today() - datetime.timedelta(days=2), 6)

        assignments = Assignment.objects.filter(cleaner=context['cleaner'],
                                                date__gte=start_date + datetime.timedelta(days=7)).order_by('date')

        pagination = Paginator(assignments, 25)
        context['page'] = pagination.get_page(kwargs['page'])

        context['assignments_due_now'] = Assignment.objects.filter(cleaner=context['cleaner'], date=start_date)

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
            context['schedule'] = Schedule.objects.get(slug=kwargs['slug'])
        except Schedule.DoesNotExist:
            Http404("Putzplan existiert nicht.")

        context['cleaners'] = Cleaner.objects.all()

        start_date = correct_dates_to_weekday(datetime.date.today() - datetime.timedelta(days=2), 6)

        assignments = context['schedule'].assignment_set.filter(date__gte=start_date).order_by('date')

        pagination = Paginator(assignments, 10*context['schedule'].cleaners_per_date)
        context['page'] = pagination.get_page(kwargs['page'])

        return self.render_to_response(context)


class ConfigView(FormView):
    template_name = 'webinterface/config.html'
    form_class = ConfigForm

    def get_context_data(self, **kwargs):
        context = super(ConfigView, self).get_context_data(**kwargs)
        context['schedule_list'] = Schedule.objects.all()
        all_active_cleaners = Cleaner.objects.filter(moved_out__gte=datetime.date.today())
        context['cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=False)
        context['no_slack_cleaner_list'] = all_active_cleaners.filter(slack_id__isnull=True)
        context['deactivated_cleaner_list'] = Cleaner.objects.exclude(moved_out__gte=datetime.date.today())
        context['schedule_group_list'] = ScheduleGroup.objects.all()
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
        for schedule in Schedule.objects.all():
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
        context['schedules'] = Schedule.objects.all().order_by('frequency')

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
            time_frame['assignments'] = []
            while date_iterator <= time_frame['end_date']:
                assignments_on_date = [date_iterator]
                schedules = []
                for schedule in context['schedules']:
                    if schedule.defined_on_date(date_iterator):
                        assignments = schedule.assignment_set.filter(date=date_iterator)
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
                        date__range=(time_frame['start_date'], time_frame['end_date']))

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

                        schedule_data = [[schedule.name, round(sum_deviation_values/len(deviation_of), 3)]]
                        schedule_data.append(sorted(deviation_of, key=itemgetter(1), reverse=True))
                        time_frame['deviations_by_schedule'].append(schedule_data)
        return context


# def update_groups_for_cleaner(cleaner, new_association):
#     """new_associations takes a list or Queryset of schedules cleaner should now be assigned to.
#     This function removes the cleaner from schedules he is not associated to anymore and adds him
#     to schedules he wasn't associated with before."""
#     try:
#         prev_association = ScheduleGroup.objects.get(cleaners=cleaner)
#
#         if prev_association != new_association:
#             prev_association.cleaners.remove(cleaner)
#             new_association.cleaners.add(cleaner)
#     except ScheduleGroup.DoesNotExist:
#         new_association.cleaners.add(cleaner)


class CleanerNewView(CreateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def form_valid(self, form):
        self.object = form.save()
        # curr_groups = form.cleaned_data['schedule_group']
        # update_groups_for_cleaner(self.object, curr_groups)
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
        # curr_group = form.cleaned_data['schedule_group']
        # update_groups_for_cleaner(self.object, curr_group)
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
