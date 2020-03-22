from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView, LogoutView
from .views import *
from .form_views import *

from django.views.generic.base import RedirectView


app_name = 'webinterface'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy("webinterface:cleaner-no-page")), name='welcome'),

    #url(r'^switch/(?P<pk>[\d]+)/(?P<answer>[\S]+)/$', DutySwitchView.as_view(), name='switch-duty-answer'),
    path('tauschen/<int:assignment_pk>/<int:page>', login_required(DutySwitchNewView.as_view()),
         name='dutyswitch-create'),

    path('tauschanfrage-akzeptieren/<int:pk>/<int:page>', login_required(DutySwitchUpdateView.as_view()),
         name='dutyswitch-accept'),

    path('tauschanfrage-loeschen/<int:pk>/<int:page>', login_required(DutySwitchDeleteView.as_view()),
         name='dutyswitch-delete'),

    path('putzen/<int:assignment_pk>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks'),
    path('putzen/<int:assignment_pk>/s<int:schedule_page>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks-back-to-schedule'),
    path('putzen/<int:assignment_pk>/p<int:cleaner_page>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks-back-to-cleaner'),

    path('geputzt/<int:assignment_pk>/<int:task_pk>', login_required(TaskCleanedView.as_view()),
         name='task-cleaned'),

    # path('putzer/<slug:slug>/seite<int:page>/', CleanerView.as_view(), name='cleaner'),
    path('du/seite<int:page>/', login_required(CleanerView.as_view()), name='cleaner'),
    path('du/', login_required(CleanerView.as_view()), name='cleaner-no-page'),

    path('putzplan-liste/', login_required(ScheduleList.as_view()), name='schedule-list'),

    path('putzplan/<slug:slug>/seite<int:page>/<slug:highlight_slug>/', login_required(ScheduleView.as_view()),
         name='schedule-view-highlight'),
    path('putzplan/<slug:slug>/seite<int:page>/', login_required(ScheduleView.as_view()), name='schedule-view'),
    path('putzplan/<slug:slug>/', login_required(ScheduleView.as_view()), name='schedule-view-no-page'),

    path('config/', staff_member_required(ConfigView.as_view(), login_url=reverse_lazy("webinterface:login")), name='config'),

    path('cleaning-week-tasks/<int:pk>/<int:page>/', staff_member_required(TaskCreateView.as_view()),
         name='cleaning-week-tasks'),

    path('cleaning-week-edit/<int:pk>/<int:page>/', staff_member_required(CleaningWeekUpdateView.as_view()),
         name='cleaning-week-edit'),

    path('cleaning-week-delete/<int:pk>/<int:page>/', staff_member_required(CleaningWeekDeleteView.as_view()),
         name='cleaning-week-delete'),

    path('assignment-create/<int:schedule_pk>/<int:page>/', staff_member_required(AssignmentCreateView.as_view()),
         name='assignment-create'),
    path('assignment-create/<int:schedule_pk>/<int:page>/<int:initial_begin>/<int:initial_end>/',
         staff_member_required(AssignmentCreateView.as_view()),
         name='assignment-create-init'),

    path('assignment-edit/<int:pk>/<int:page>/', staff_member_required(AssignmentUpdateView.as_view()),
         name='assignment-edit'),

    path('schedule-new/', staff_member_required(ScheduleNewView.as_view()), name='schedule-new'),
    path('schedule-edit/<int:pk>/', staff_member_required(ScheduleUpdateView.as_view()),
         name='schedule-edit'),
    path('schedule-delete/<int:pk>/', staff_member_required(ScheduleDeleteView.as_view()),
         name='schedule-delete'),
    path('schedule/<int:pk>/tasks/', staff_member_required(ScheduleTaskList.as_view()),
         name='schedule-task-list'),
    path('schedule/<int:pk>/tasks/new/', staff_member_required(TaskTemplateNewView.as_view()),
         name='schedule-task-new'),

    path('schedule-group-new/', staff_member_required(ScheduleGroupNewView.as_view()),
         name='schedule-group-new'),
    path('schedule-group-edit/<int:pk>/', staff_member_required(ScheduleGroupUpdateView.as_view()),
         name='schedule-group-edit'),

    path('putzer/neu/', staff_member_required(CleanerNewView.as_view()), name='cleaner-new'),
    path('putzer/<int:pk>/', staff_member_required(CleanerUpdateView.as_view()),
         name='cleaner-edit'),
    path('putzer/<int:pk>/zugehoerigkeiten/', staff_member_required(AffiliationNewView.as_view()),
         name='affiliation-list'),


    path('cleaner-delete/<int:pk>/', staff_member_required(CleanerDeleteView.as_view()), name='cleaner-delete'),

    path('affiliation-edit/<int:pk>/', staff_member_required(AffiliationUpdateView.as_view()), name='affiliation-edit'),

    path('affiliation-delete/<int:pk>/', staff_member_required(AffiliationDeleteView.as_view()),
         name='affiliation-delete'),

    path('task-edit/<int:pk>/', staff_member_required(TaskTemplateUpdateView.as_view()), name='task-edit'),


    path('login/', LoginView.as_view(template_name="webinterface/generic_form.html", extra_context={'title': "Login"},
                                     authentication_form=AuthFormWithSubmit), name='login'),
    path('login-per-klick', LoginByClickView.as_view(), name='login-by-click'),
    path('logout/', login_required(LogoutView.as_view()), name='logout'),
]
