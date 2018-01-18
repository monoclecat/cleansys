from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import *

from django.views.generic.base import RedirectView
import datetime


app_name = 'webinterface'
urlpatterns = [
    path('', WelcomeView.as_view(), name='welcome'),
    #url(r'^$', WelcomeView.as_view(), name='welcome'),

    #url(r'^switch/(?P<pk>[\d]+)/(?P<answer>[\S]+)/$', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('switch/<int:pk>/<answer>/', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('switch/<int:pk>/', DutySwitchView.as_view(), name='switch-duty'),

    path('clean/<int:assignment_pk>/', AssignmentView.as_view(), name='clean-duty'),

    path('putzer/<slug:slug>/seite<int:page>/', CleanerView.as_view(), name='cleaner-duties'),

    path('putzplan/<slug:slug>/seite<int:page>/<slug:cleaner_slug>/', CleaningScheduleView.as_view(),
         name='schedule-view-highlight'),
    path('putzplan/<slug:slug>/seite<int:page>/', CleaningScheduleView.as_view(), name='schedule-view'),

    path('config/', login_required(ConfigView.as_view()), name='config'),
    path('results/', RedirectView.as_view(
         url=reverse_lazy('webinterface:results',
                    kwargs={'from_day': datetime.datetime.now().day, 'from_month': datetime.datetime.now().month,
                            'from_year': datetime.datetime.now().year,
                            'to_day': (datetime.datetime.now() + datetime.timedelta(days=30)).day,
                            'to_month': (datetime.datetime.now() + datetime.timedelta(days=30)).month,
                            'to_year': (datetime.datetime.now() + datetime.timedelta(days=30)).year})),
         name='results-now'),

    path('results/<int:from_day>-<int:from_month>-<int:from_year>/'
         '<int:to_day>-<int:to_month>-<int:to_year>/<options>/',
         login_required(ResultsView.as_view()), name='results'),
    path('results/<int:from_day>-<int:from_month>-<int:from_year>/'
         '<int:to_day>-<int:to_month>-<int:to_year>',
         login_required(ResultsView.as_view()), name='results'),

    path('cleaner-new/', login_required(CleanerNewView.as_view()), name='cleaner-new'),
    path('cleaner-edit/<int:pk>/', login_required(CleanerUpdateView.as_view()),
         name='cleaner-edit'),
    path('cleaner-delete/<int:pk>/', login_required(CleanerDeleteView.as_view()), name='cleaner-delete'),

    path('cleaning-schedule-new/', login_required(CleaningScheduleNewView.as_view()), name='cleaning-schedule-new'),
    path('cleaning-schedule-edit/<int:pk>/', login_required(CleaningScheduleUpdateView.as_view()),
         name='cleaning-schedule-edit'),
    path('cleaning-schedule-delete/<int:pk>/', login_required(CleaningScheduleDeleteView.as_view()),
         name='cleaning-schedule-delete'),

    path('cleaning-schedule-group-new/', login_required(CleaningScheduleGroupNewView.as_view()),
         name='cleaning-schedule-group-new'),
    path('cleaning-schedule-group-edit/<int:pk>/', login_required(CleaningScheduleGroupUpdateView.as_view()),
         name='cleaning-schedule-group-edit'),
    path('cleaning-schedule-group-delete/<int:pk>/', login_required(CleaningScheduleGroupDeleteView.as_view()),
         name='cleaning-schedule-group-delete'),

    path('login/', login_view, name='login'),
    path('logout/', login_required(login_view), name='logout'),
]