from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView, LogoutView
from .views import *

from django.views.generic.base import RedirectView
import datetime


app_name = 'webinterface'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy("webinterface:cleaner", kwargs={'page': 1})), name='welcome'),

    #url(r'^switch/(?P<pk>[\d]+)/(?P<answer>[\S]+)/$', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('switch/<int:pk>/<answer>/', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('switch/<int:pk>/', DutySwitchView.as_view(), name='switch-duty'),

    path('clean/<int:assignment_pk>/', TaskView.as_view(), name='clean-duty'),

    # path('putzer/<slug:slug>/seite<int:page>/', CleanerView.as_view(), name='cleaner'),
    path('du/seite<int:page>/', login_required(CleanerView.as_view()), name='cleaner'),

    path('putzplaene/', login_required(ScheduleList.as_view()),
         name='schedule-list'),

    #path('putzplan/<slug:slug>/seite<int:page>/<slug:cleaner_slug>/', ScheduleView.as_view(),
    #     name='schedule-view-highlight'),
    path('putzplan/<slug:slug>/seite<int:page>/', ScheduleView.as_view(), name='schedule-view'),

    path('config/', staff_member_required(ConfigView.as_view(), login_url=reverse_lazy("webinterface:login")), name='config'),
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

    path('beschwerde/', login_required(ComplaintNewView.as_view()), name='complaint-new'),

    path('config-edit/', login_required(ConfigUpdateView.as_view()), name='config-edit'),

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

    path('login/', LoginView.as_view(template_name="webinterface/generic_form.html", extra_context={'title': "Login"},
                                     authentication_form=AuthFormWithSubmit), name='login'),
    path('login-per-klick', LoginByClickView.as_view(), name='login-by-click'),
    path('logout/', login_required(LogoutView.as_view()), name='logout'),
]
