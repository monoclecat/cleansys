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
                            'to_year': (datetime.datetime.now() + datetime.timedelta(days=30)).year})),
        name='results-now'),

    url(r'^results/(?P<from_day>[\d]+)-(?P<from_month>[\d]+)-(?P<from_year>[\d]+)/'
        r'(?P<to_day>[\d]+)-(?P<to_month>[\d]+)-(?P<to_year>[\d]+)/(?P<options>[\w]+)$',
        login_required(ResultsView.as_view()), name='results'),
    url(r'^results/(?P<from_day>[\d]+)-(?P<from_month>[\d]+)-(?P<from_year>[\d]+)/'
        r'(?P<to_day>[\d]+)-(?P<to_month>[\d]+)-(?P<to_year>[\d]+)$',
        login_required(ResultsView.as_view()), name='results'),

    url(r'^cleaner-new/$', login_required(CleanersNewView.as_view()), name='cleaners-new'),
    url(r'^cleaner-deactivate/(?P<pk>[\d]+)/$', login_required(CleanersDeactivateView.as_view()),
        name='cleaners-deactivate'),
    url(r'^cleaner-edit/(?P<pk>[\d]+)/$', login_required(CleanersUpdateView.as_view()),
        name='cleaners-edit'),

    url(r'^cleaning-schedule-new/$', login_required(CleaningScheduleNewView.as_view()), name='cleaning-schedule-new'),
    url(r'^cleaning-schedule-deactivate/(?P<pk>[\d]+)/$', login_required(CleaningScheduleDeactivateView.as_view()),
        name='cleaning-schedule-deactivate'),
    url(r'^cleaning-schedule-edit/(?P<pk>[\d]+)/$', login_required(CleaningScheduleUpdateView.as_view()),
        name='cleaning-schedule-edit'),

    url(r'^login/$', login_view, name='login'),
    url(r'^logout/$', login_required(login_view), name='logout'),
]