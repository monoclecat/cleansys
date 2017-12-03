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


class WelcomeView(TemplateView):
    template_name = "webinterface/welcome.html"


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


class CleaningPlanView(ListView):
    model = CleaningPlan
    template_name = 'webinterface/cleaningplan.html'


class CleaningPlanNewView(CreateView):
    form_class = CleaningPlanForm
    model = CleaningPlan
    success_url = reverse_lazy('webinterface:cleaning-plans')
    template_name = 'webinterface/cleaningplan_new.html'


class CleaningPlanDeleteView(DeleteView):
    model = CleaningPlan
    success_url = reverse_lazy('webinterface:cleaning-plans')
    template_name = 'webinterface/cleaningplan_delete.html'


class CleaningPlanUpdateView(UpdateView):
    form_class = CleaningPlanForm
    model = CleaningPlan
    success_url = reverse_lazy('webinterface:cleaning-plans')
    template_name = 'webinterface/cleaningplan_edit.html'


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
