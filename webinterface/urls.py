from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView, LogoutView
from .views import *

from django.views.generic.base import RedirectView


app_name = 'webinterface'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy("webinterface:cleaner", kwargs={'page': 1})), name='welcome'),

    #url(r'^switch/(?P<pk>[\d]+)/(?P<answer>[\S]+)/$', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('switch/<int:pk>/<answer>/', login_required(DutySwitchView.as_view()), name='switch-duty-answer'),
    path('switch/<int:pk>/', login_required(DutySwitchView.as_view()), name='switch-duty'),

    path('clean/<int:assignment_pk>/', login_required(TaskView.as_view()), name='clean-duty'),

    # path('putzer/<slug:slug>/seite<int:page>/', CleanerView.as_view(), name='cleaner'),
    path('du/seite<int:page>/', login_required(CleanerView.as_view()), name='cleaner'),

    path('putzplaene/', login_required(ScheduleList.as_view()),
         name='schedule-list'),

    #path('putzplan/<slug:slug>/seite<int:page>/<slug:cleaner_slug>/', ScheduleView.as_view(),
    #     name='schedule-view-highlight'),
    path('putzplan/<slug:slug>/seite<int:page>/', login_required(ScheduleView.as_view()), name='schedule-view'),

    path('config/', staff_member_required(ConfigView.as_view(), login_url=reverse_lazy("webinterface:login")), name='config'),
    path('results/', staff_member_required(RedirectView.as_view(
         url=reverse_lazy('webinterface:results',
                    kwargs={'from_day': timezone.now().date().day, 'from_month': timezone.now().date().month,
                            'from_year': timezone.now().date().year,
                            'to_day': (timezone.now().date() + timezone.timedelta(days=30)).day,
                            'to_month': (timezone.now().date() + timezone.timedelta(days=30)).month,
                            'to_year': (timezone.now().date() + timezone.timedelta(days=30)).year}))),
         name='results-now'),

    path('results/<int:from_day>-<int:from_month>-<int:from_year>/'
         '<int:to_day>-<int:to_month>-<int:to_year>/<options>/',
         staff_member_required(ResultsView.as_view()), name='results'),
    path('results/<int:from_day>-<int:from_month>-<int:from_year>/'
         '<int:to_day>-<int:to_month>-<int:to_year>',
         staff_member_required(ResultsView.as_view()), name='results'),

    path('beschwerde/<slug:slug>/', login_required(ComplaintNewView.as_view()), name='complaint-new'),
    path('beschwerde/<slug:slug>/<int:pk>/', login_required(ComplaintView.as_view()), name='complaint'),

    path('config-edit/', staff_member_required(ConfigUpdateView.as_view()), name='config-edit'),

    path('cleaner-new/', staff_member_required(CleanerNewView.as_view()), name='cleaner-new'),
    path('cleaner-edit/<int:pk>/', staff_member_required(CleanerUpdateView.as_view()),
         name='cleaner-edit'),
    path('cleaner-delete/<int:pk>/', staff_member_required(CleanerDeleteView.as_view()), name='cleaner-delete'),

    path('cleaning-schedule-new/', staff_member_required(CleaningScheduleNewView.as_view()), name='cleaning-schedule-new'),
    path('cleaning-schedule-edit/<int:pk>/', staff_member_required(CleaningScheduleUpdateView.as_view()),
         name='cleaning-schedule-edit'),
    path('cleaning-schedule-delete/<int:pk>/', staff_member_required(CleaningScheduleDeleteView.as_view()),
         name='cleaning-schedule-delete'),

    path('cleaning-schedule-group-new/', staff_member_required(CleaningScheduleGroupNewView.as_view()),
         name='cleaning-schedule-group-new'),
    path('cleaning-schedule-group-edit/<int:pk>/', staff_member_required(CleaningScheduleGroupUpdateView.as_view()),
         name='cleaning-schedule-group-edit'),
    path('cleaning-schedule-group-delete/<int:pk>/', staff_member_required(CleaningScheduleGroupDeleteView.as_view()),
         name='cleaning-schedule-group-delete'),

    path('login/', LoginView.as_view(template_name="webinterface/generic_form.html", extra_context={'title': "Login"},
                                     authentication_form=AuthFormWithSubmit), name='login'),
    path('login-per-klick', LoginByClickView.as_view(), name='login-by-click'),
    path('logout/', login_required(LogoutView.as_view()), name='logout'),
]
