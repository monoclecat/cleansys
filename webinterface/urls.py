from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from .views import *

from django.views.generic.base import RedirectView
import datetime


app_name = 'webinterface'
urlpatterns = [
    url(r'^$', WelcomeView.as_view(), name='welcome'),

    url(r'^switch/(?P<duty_pk>[\d]+)/(?P<old_cleaner_pk>[\d]+)/$',
        DutySwitchView.as_view(), name='switch-duty'),

    url(r'^(?P<pk>[\d]+)/(?P<slug>[\S]+)/(?P<page>[\d]+)/$', CleaningDutyView.as_view(), name='cleaner-duties'),
    url(r'^(?P<pk>[\d]+)/(?P<slug>[\S]+)/$', CleaningDutyView.as_view(), name='cleaner-duties-page1'),

    url(r'^duties/(?P<pk>[\d]+)/(?P<page>[\d]+)/$', CleaningDutyAllView.as_view(), name='duties-all-with-pk'),
    url(r'^duties/(?P<pk>[\d]+)/$', CleaningDutyAllView.as_view(), name='duties-all-with-pk-page1'),
    url(r'^duties/all/(?P<page>[\d]*)/$', CleaningDutyAllView.as_view(), name='duties-all-no-pk'),
    url(r'^duties/all/$', CleaningDutyAllView.as_view(), name='duties-all-no-pk-page1'),

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

    url(r'^cleaner-new/$', login_required(CleanerNewView.as_view()), name='cleaner-new'),
    url(r'^cleaner-edit/(?P<pk>[\d]+)/$', login_required(CleanerUpdateView.as_view()),
        name='cleaner-edit'),
    url(r'^cleaner-delete/(?P<pk>[\d]+)/$', login_required(CleanerDeleteView.as_view()), name='cleaner-delete'),

    url(r'^cleaning-schedule-new/$', login_required(CleaningScheduleNewView.as_view()), name='cleaning-schedule-new'),
    url(r'^cleaning-schedule-edit/(?P<pk>[\d]+)/$', login_required(CleaningScheduleUpdateView.as_view()),
        name='cleaning-schedule-edit'),
    url(r'^cleaning-schedule-delete/(?P<pk>[\d]+)/$', login_required(CleaningScheduleDeleteView.as_view()),
        name='cleaning-schedule-delete'),

    url(r'^login/$', login_view, name='login'),
    url(r'^logout/$', login_required(login_view), name='logout'),
]