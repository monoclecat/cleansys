from .forms import *
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.http import HttpResponseRedirect
from django.core.exceptions import SuspiciousOperation
from django.http import Http404


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

        schedule_group = form.cleaned_data['schedule_group']
        beginning = form.cleaned_data['schedule_group__action_date']
        Affiliation.objects.create(cleaner=self.object, group=schedule_group, beginning=beginning)
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
        self.object = form.save(commit=False)
        self.object.cleaner = cleaner
        self.object.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:cleaner-edit', kwargs={'pk': cleaner.pk}))


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
        self.object = form.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:cleaner-edit', kwargs={'pk': self.object.cleaner.pk}))


class CleaningDayUpdateView(UpdateView):
    form_class = CleaningDayForm
    model = CleaningWeek
    success_url = reverse_lazy('webinterface:config')
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Bearbeite Putzdienst"
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(reverse_lazy('webinterface:schedule-view',
                                                 kwargs={'slug': self.object.schedule.slug, 'page': 1}))


class TaskTemplateNewView(CreateView):
    form_class = TaskTemplateForm
    model = TaskTemplate
    template_name = 'webinterface/generic_form.html'

    def __init__(self):
        self.schedule = None
        self.object = None
        super().__init__()

    def get(self, request, *args, **kwargs):
        try:
            self.schedule = Schedule.objects.get(pk=kwargs['pk'])
        except Schedule.DoesNotExist:
            Http404('Putzplan, für den die Aufgabe erstellt werden soll, existiert nicht!')
        self.success_url = reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.schedule.pk})
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['schedule'] = self.schedule
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
        return HttpResponseRedirect(
            reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.kwargs['pk']}))


class TaskTemplateUpdateView(UpdateView):
    form_class = TaskTemplateForm
    model = TaskTemplate
    template_name = 'webinterface/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Bearbeite Aufgabe"
        return context

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(
            reverse_lazy('webinterface:schedule-task-list', kwargs={'pk': self.object.schedule.pk}))


class AssignmentCleaningView(UpdateView):
    template_name = "webinterface/clean_duty.html"
    model = Assignment
    form_class = AssignmentCleaningForm
    pk_url_kwarg = "assignment_pk"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        try:
            context['tasks'] = self.object.cleaning_day.task_set.all()
        except CleaningWeek.DoesNotExist:
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
                task = TaskTemplate.objects.get(pk=request.POST['task_pk'])

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

            except (TaskTemplate.DoesNotExist, Assignment.DoesNotExist):
                raise SuspiciousOperation("TaskTemplate or Assignment does not exist.")
        else:
            return super().post(args, kwargs)


