from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from .views import *

from django.views.generic.base import RedirectView
import datetime


app_name = 'webinterface'
urlpatterns = [
    url(r'^$', login_required(WelcomeView.as_view()), name='welcome'),

    url(r'^config/$', login_required(ConfigView.as_view()), name='config'),
    url(r'^results/$', RedirectView.as_view(
        url=reverse_lazy('webinterface:results',
                    kwargs={'from_day': datetime.datetime.now().day, 'from_month': datetime.datetime.now().month,
                            'from_year': datetime.datetime.now().year,
                            'to_day': (datetime.datetime.now() + datetime.timedelta(days=30)).day,
                            'to_month': (datetime.datetime.now() + datetime.timedelta(days=30)).month,
                            'to_year': (datetime.datetime.now() + datetime.timedelta(days=30)).year})), name='results-now'),
    url(r'^results/(?P<from_day>[\d]+)-(?P<from_month>[\d]+)-(?P<from_year>[\d]+)/(?P<to_day>[\d]+)-(?P<to_month>[\d]+)-(?P<to_year>[\d]+)$', login_required(ResultsView.as_view()), name='results'),

    url(r'^cleaners-new/$', login_required(CleanersNewView.as_view()), name='cleaners-new'),
    url(r'^cleaners-delete/(?P<pk>[\w]+)/$', login_required(CleanersDeleteView.as_view()),
        name='cleaners-delete'),
    url(r'^cleaners-edit/(?P<pk>[\w]+)/$', login_required(CleanersUpdateView.as_view()),
        name='cleaners-edit'),

    url(r'^cleaning-schedules-new/$', login_required(CleaningScheduleNewView.as_view()), name='cleaning-schedule-new'),
    url(r'^cleaning-schedules-delete/(?P<pk>[\w]+)/$', login_required(CleaningScheduleDeleteView.as_view()),
        name='cleaning-schedule-delete'),
    url(r'^cleaning-schedules-edit/(?P<pk>[\w]+)/$', login_required(CleaningScheduleUpdateView.as_view()),
        name='cleaning-schedule-edit'),

    url(r'^login/$', login_view, name='login'),
    url(r'^logout/$', login_required(login_view), name='logout'),
]