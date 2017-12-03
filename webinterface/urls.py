from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from .views import *

app_name = 'webinterface'
urlpatterns = [
    url(r'^$', login_required(WelcomeView.as_view()), name='welcome'),

    url(r'^cleaners/$', login_required(CleanersView.as_view()), name='cleaners'),
    url(r'^cleaners-new/$', login_required(CleanersNewView.as_view()), name='cleaners-new'),
    url(r'^cleaners-delete/(?P<pk>[\w]+)/$', login_required(CleanersDeleteView.as_view()),
        name='cleaners-delete'),
    url(r'^cleaners-edit/(?P<pk>[\w]+)/$', login_required(CleanersUpdateView.as_view()),
        name='cleaners-edit'),

    url(r'^cleaning-schedules/$', login_required(CleaningPlanView.as_view()), name='cleaning-plans'),
    url(r'^cleaning-schedule-new/$', login_required(CleaningPlanNewView.as_view()), name='cleaning-plan-new'),
    url(r'^cleaning-schedule-delete/(?P<pk>[\w]+)/$', login_required(CleaningPlanDeleteView.as_view()),
        name='cleaning-plan-delete'),
    url(r'^cleaning-schedule-edit/(?P<pk>[\w]+)/$', login_required(CleaningPlanUpdateView.as_view()),
        name='cleaning-plan-edit'),

    url(r'^login/$', login_view, name='login'),
    url(r'^logout/$', login_required(login_view), name='logout'),
]