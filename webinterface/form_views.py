from .forms import *
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView, FormView
from django.http import HttpResponseRedirect
from django.core.exceptions import SuspiciousOperation
from django.http import Http404
from django.core.exceptions import ValidationError


class ScheduleNewView(CreateView):
    form_class = ScheduleForm
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erzeuge neuen Putzplan"
        return context

    def form_valid(self, form):
        self.object = form.save()
        schedule_group = form.cleaned_data['schedule_group']
        for group in schedule_group:
            group.schedules.add(self.object)
        return HttpResponseRedirect(self.get_success_url())


class ScheduleUpdateView(UpdateView):
    form_class = ScheduleForm
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzplan"
        return context

    def form_valid(self, form):
        self.object = form.save()

        schedule_group = form.cleaned_data['schedule_group']
        for group in schedule_group:
            group.schedules.add(self.object)

        return HttpResponseRedirect(self.get_success_url())


class ScheduleDeleteView(DeleteView):
    model = Schedule
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzplan"
        return context


class ScheduleGroupNewView(CreateView):
    form_class = ScheduleGroupForm
    model = ScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erstelle eine neue Putzplan-Gruppierung"
        return context


class ScheduleGroupUpdateView(UpdateView):
    form_class = ScheduleGroupForm
    model = ScheduleGroup
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere eine Putzplan-Gruppierung"
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

    def form_valid(self, form):
        self.object = form.save()
        self.object.user.email = form.cleaned_data.get('email')
        self.object.user.save()

        return HttpResponseRedirect(self.get_success_url())


class CleanerUpdateView(UpdateView):
    form_class = CleanerForm
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Ändere Putzerprofil"
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.object.user.email != form.cleaned_data.get('email'):
            self.object.user.email = form.cleaned_data.get('email')
            self.object.user.save()

        return HttpResponseRedirect(self.get_success_url())


class CleanerDeleteView(DeleteView):
    model = Cleaner
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzer"
        return context


class AffiliationNewView(CreateView):
    form_class = AffiliationForm
    model = Affiliation
    template_name = 'webinterface/affiliation_list.html'

    def __init__(self):
        self.cleaner = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.cleaner = Cleaner.objects.get(pk=kwargs['pk'])
        except Cleaner.DoesNotExist:
            Http404('Putzer, für den Zugehörigkeit geändert werden soll, existiert nicht!')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cleaner'] = self.cleaner
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Zugehörigkeiten von {}".format(self.cleaner.name)
        context['cleaner'] = self.cleaner
        return context

    def form_valid(self, form):
        if 'pk' not in self.kwargs:
            raise OperationalError('No pk is supplied in AffiliationNewView!')
        try:
            cleaner = Cleaner.objects.get(pk=self.kwargs['pk'])
        except Cleaner.DoesNotExist:
            raise OperationalError('PK provided in URL does not belong to any Cleaner!')
        # self.object = form.save(commit=False)
        beginning_date = datetime.datetime.strptime(form.data['beginning'], "%d.%m.%Y")
        end_date = datetime.datetime.strptime(form.data['end'], "%d.%m.%Y")
        self.object = Affiliation(cleaner=cleaner,
                                  group=ScheduleGroup.objects.get(pk=form.data['group']),
                                  beginning=date_to_epoch_week(beginning_date),
                                  end=date_to_epoch_week(end_date))
        self.object.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:affiliation-list', kwargs={'pk': cleaner.pk}))


class AffiliationUpdateView(UpdateView):
    form_class = AffiliationForm
    model = Affiliation
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Bearbeite Zugehörigkeit"
        return context

    def form_valid(self, form):
        beginning_date = datetime.datetime.strptime(form.data['beginning'], "%d.%m.%Y")
        end_date = datetime.datetime.strptime(form.data['end'], "%d.%m.%Y")
        self.object.beginning = date_to_epoch_week(beginning_date)
        self.object.end = date_to_epoch_week(end_date)
        self.object.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:affiliation-list',
                                                 kwargs={'pk': self.object.cleaner.pk}))


class AffiliationDeleteView(DeleteView):
    model = Affiliation
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Zugehörigkeit"
        return context

    def delete(self, request, *args, **kwargs):
        affiliation = Affiliation.objects.get(pk=kwargs['pk'])
        self.success_url = reverse_lazy('webinterface:affiliation-list', kwargs={'pk': affiliation.cleaner.pk})
        return super().delete(request, *args, **kwargs)


class CleaningWeekUpdateView(UpdateView):
    form_class = CleaningWeekForm
    model = CleaningWeek
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Putzwoche deaktivieren"
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view',
                                                 kwargs={'slug': self.object.schedule.slug,
                                                         'page': self.kwargs['page']}))


class CleaningWeekDeleteView(DeleteView):
    model = CleaningWeek
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_delete_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Putzwoche"
        return context

    def delete(self, request, *args, **kwargs):
        cleaning_week = CleaningWeek.objects.get(pk=kwargs['pk'])
        self.success_url = reverse_lazy('webinterface:schedule-view', kwargs={'slug': cleaning_week.schedule.slug,
                                                                              'page': kwargs['page']})
        return super().delete(request, *args, **kwargs)


class AssignmentCreateView(FormView):
    template_name = 'webinterface/generic_form.html'
    form_class = AssignmentCreateForm

    def __init__(self):
        self.schedule = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.schedule = Schedule.objects.get(pk=kwargs['schedule_pk'])
        except Cleaner.DoesNotExist:
            Http404('Putzplan, für den Zugehörigkeit geändert werden soll, existiert nicht!')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'initial_begin' in self.kwargs and 'initial_end' in self.kwargs:
            kwargs['initial_begin'] = self.kwargs['initial_begin']
            kwargs['initial_end'] = self.kwargs['initial_end']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erzeuge Putzdienste für {}".format(self.schedule.name)
        context['schedule'] = self.schedule
        context['page'] = self.kwargs['page']
        return context

    def form_valid(self, form):
        from_week = date_to_epoch_week(form.cleaned_data['from_date'])
        to_week = date_to_epoch_week(form.cleaned_data['to_date'])
        mode = form.cleaned_data['mode']

        self.schedule.create_assignments_over_timespan(start_week=from_week, end_week=to_week, mode=int(mode))

        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view', kwargs={'slug': self.schedule.slug,
                                                                                       'page': self.kwargs['page']}))


class AssignmentUpdateView(UpdateView):
    form_class = AssignmentForm
    model = Assignment
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Einzelnen Putzdienst bearbeiten"
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view',
                                                 kwargs={'slug': self.object.schedule.slug,
                                                         'page': self.kwargs['page']}))


class TaskTemplateNewView(CreateView):
    form_class = TaskTemplateForm
    model = TaskTemplate
    template_name = 'webinterface/generic_form.html'

    def __init__(self):
        self.schedule = None
        self.object = None
        super().__init__()

    # def get(self, request, *args, **kwargs):
    #     try:
    #         self.schedule = Schedule.objects.get(pk=kwargs['pk'])
    #     except Schedule.DoesNotExist:
    #         Http404('Putzplan, für den die Aufgabe erstellt werden soll, existiert nicht!')
    #     self.success_url = reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.schedule.pk})
    #     return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['schedule'] = Schedule.objects.get(pk=self.kwargs['pk'])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Erstelle Aufgabe"
        return context

    def form_valid(self, form):
        if 'pk' not in self.kwargs:
            raise OperationalError('No pk is supplied in TaskTemplateNewView!')
        try:
            schedule = Schedule.objects.get(pk=self.kwargs['pk'])
        except Schedule.DoesNotExist:
            raise OperationalError('PK provided in URL does not belong to any Schedule!')
        self.object = form.save(commit=False)
        self.object.schedule = schedule
        self.object.save()
        for cleaning_week in schedule.cleaningweek_set.all():
            cleaning_week.tasks_valid = False
            cleaning_week.save()
        return HttpResponseRedirect(
            reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.kwargs['pk']}))


class TaskTemplateUpdateView(UpdateView):
    form_class = TaskTemplateForm
    model = TaskTemplate
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Bearbeite Aufgabe"
        # TODO Add context schedule here so we don't have to work with string concat in forms.py l.405
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(
            reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.object.schedule.pk}))


class TaskCreateView(FormView):
    template_name = 'webinterface/generic_form.html'
    form_class = TaskCreateForm

    def __init__(self):
        self.cleaning_week = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.cleaning_week = CleaningWeek.objects.get(pk=kwargs['pk'])
        except Cleaner.DoesNotExist:
            Http404('Putzplan, für den Zugehörigkeit geändert werden soll, existiert nicht!')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cleaning_week'] = self.cleaning_week
        context['title'] = "Erzeuge Aufgaben für {} in der Woche von {} bis {}".\
            format(self.cleaning_week.schedule.name, self.cleaning_week.week_start(), self.cleaning_week.week_end())

        context['cleaning_week_tasks'] = self.cleaning_week.task_set.all()
        context['missing_schedule_task_templates'] = self.cleaning_week.task_templates_missing()

        context['page'] = self.kwargs['page']
        return context

    def form_valid(self, form):
        self.cleaning_week.create_missing_tasks()

        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view',
                                                 kwargs={'slug': self.cleaning_week.schedule.slug,
                                                         'page': self.kwargs['page']}))


class TaskCleanedView(UpdateView):
    form_class = TaskCleanedForm
    model = Task
    template_name = 'webinterface/generic_form.html'
    pk_url_kwarg = "task_pk"

    def __init__(self):
        self.assignment = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.assignment = Assignment.objects.get(pk=kwargs['assignment_pk'])
        except Cleaner.DoesNotExist:
            Http404('Putzdienst, für dessen eine Aufgabe als geputzt gesetzt werden soll, existiert nicht!')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Setze eine Aufgabe als 'geputzt'"
        context['assignment'] = self.assignment
        context['help_text'] = self.object.template.task_help_text
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(
            reverse_lazy('webinterface:assignment-tasks', kwargs={'assignment_pk': self.assignment.pk}))


class DutySwitchNewView(CreateView):
    form_class = DutySwitchCreateForm
    model = DutySwitch
    template_name = 'webinterface/generic_form.html'

    def __init__(self):
        self.assignment = None
        self.object = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        self.assignment = Assignment.objects.get(pk=self.kwargs['assignment_pk'])
        self.success_url = reverse_lazy('webinterface:cleaner', kwargs={'page': kwargs['page']})
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Gebe einen Putzdienst-Tausch in Auftrag"
        context['assignment'] = self.assignment
        context['page'] = self.kwargs['page']
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.requester_assignment = self.assignment
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class DutySwitchUpdateView(UpdateView):
    form_class = DutySwitchAcceptForm
    model = DutySwitch
    template_name = 'webinterface/generic_form.html'

    def __init__(self):
        self.cleaner = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.cleaner = Cleaner.objects.get(slug=request.user.username)
        except Cleaner.DoesNotExist:
            Http404('Du bist als ein Nutzer angemeldet, der keinem Putzer zugeordnet ist!')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cleaner'] = self.cleaner
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Tauschanfrage"
        context['page'] = self.kwargs['page']
        # context['requester '] = DutySwitch.objects.get(pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(
            reverse_lazy('webinterface:cleaner', kwargs={'page': self.kwargs['page']}))


class DutySwitchDeleteView(DeleteView):
    model = DutySwitch
    success_url = reverse_lazy('webinterface:cleaner')
    template_name = 'webinterface/generic_delete_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.success_url = reverse_lazy('webinterface:cleaner', kwargs={'page': kwargs['page']})
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Lösche Tauschanfrage"
        context['cancel_url'] = self.success_url
        return context


class AssignmentTasksView(UpdateView):
    template_name = "webinterface/assignment_tasks.html"
    model = Assignment
    form_class = AssignmentCleaningForm
    pk_url_kwarg = "assignment_pk"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        try:
            context['tasks'] = self.object.cleaning_week.task_set.all()
        except CleaningWeek.DoesNotExist:
            logging.error("CleaningWeek does not exist on date!")
            raise Exception("CleaningWeek does not exist on date!")

        context['assignment'] = self.object
        return context

    # def post(self, request, *args, **kwargs):
    #     try:
    #         assignment = Assignment.objects.get(pk=kwargs['assignment_pk'])
    #         self.success_url = reverse_lazy(
    #                 'webinterface:clean-duty',
    #                 kwargs={'assignment_pk': assignment.pk})
    #     except Assignment.DoesNotExist:
    #         raise SuspiciousOperation("Assignment does not exist.")
    #     self.object = self.get_object()
    #
    #     if 'cleaned' in request.POST:
    #         try:
    #             assignment = Assignment.objects.get(pk=kwargs['assignment_pk'])
    #             task = TaskTemplate.objects.get(pk=request.POST['task_pk'])
    #
    #             if task.cleaned_by:
    #                 if task.cleaned_by == assignment:
    #                     task.cleaned_by = None
    #                 else:
    #                     context = self.get_context_data(**kwargs)
    #                     context['already_cleaned_error'] = "{} wurde in der Zwischenzeit schon von {} gemacht!".format(
    #                         task.name, task.cleaned_by.cleaner)
    #                     return self.render_to_response(context)
    #             else:
    #                 task.cleaned_by = assignment
    #             task.save()
    #             return HttpResponseRedirect(self.get_success_url())
    #
    #         except (TaskTemplate.DoesNotExist, Assignment.DoesNotExist):
    #             raise SuspiciousOperation("TaskTemplate or Assignment does not exist.")
    #     else:
    #         return super().post(args, kwargs)


