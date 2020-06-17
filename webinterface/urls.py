from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from webinterface.views import *
from webinterface.api_views import *
from webinterface.form_views import *
from webinterface.decorators import *
from django.conf.urls import include
from rest_framework import routers

from django.views.generic.base import RedirectView

router = routers.DefaultRouter()  # https://www.django-rest-framework.org/api-guide/routers/#defaultrouter
router.register(r'schedules', ScheduleViewSet)
router.register(r'schedulegroups', ScheduleGroupViewSet)
router.register(r'users', UserViewSet)
router.register(r'cleaners', CleanerViewSet)
router.register(r'affiliations', AffiliationViewSet)
router.register(r'cleaningweeks', CleaningWeekViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'tasktemplates', TaskTemplateViewSet)
router.register(r'task', TaskViewSet)
router.register(r'dutyswitches', DutySwitchViewSet)

app_name = 'webinterface'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy("webinterface:cleaner-no-page")), name='welcome'),
    path('login/', LoginView.as_view(template_name="webinterface/generic_form.html",
                                     extra_context={'title': "Login", 'add_home_button': True},
                                     authentication_form=AuthFormWithSubmit), name='login'),
    path('login-per-klick/', LoginByClickView.as_view(), name='login-by-click'),
    path('logout/', login_required(LogoutView.as_view()), name='logout'),
    path('admin/', must_be_admin(AdminView.as_view()), name='admin'),
    path('documentation/', DocumentationView.as_view(), name='docs'),
    path('admin/faq', must_be_admin(AdminFAQView.as_view()), name='admin-faq'),
    path('admin/daten', must_be_admin(AdminUpdateView.as_view()), name='admin-edit'),

    path('affiliation-edit/<int:pk>/', must_be_admin(AffiliationUpdateView.as_view()), name='affiliation-edit'),
    path('affiliation-delete/<int:pk>/', must_be_admin(AffiliationDeleteView.as_view()),
         name='affiliation-delete'),
    path('putzer/<int:pk>/zugehoerigkeiten/', login_required(AffiliationNewView.as_view()),
         name='affiliation-list'),
    path('putzer/<int:pk>/zugehoerigkeiten/p<int:cleaner_page>/', login_required(AffiliationNewView.as_view()),
         name='affiliation-list-with-cleaner-page'),

    path('putzen/<int:cleaning_week_pk>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks'),
    path('putzen/<int:cleaning_week_pk>/s<int:schedule_page>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks-back-to-schedule'),
    path('putzen/<int:cleaning_week_pk>/p<int:cleaner_page>/', login_required(AssignmentTasksView.as_view()),
         name='assignment-tasks-back-to-cleaner'),
    path('assignment-create/<int:schedule_pk>/<int:page>/', must_be_admin(AssignmentCreateView.as_view()),
         name='assignment-create-back-to-schedule'),
    path('assignment-create/<int:schedule_pk>/<int:page>/<int:initial_begin>/<int:initial_end>/',
         must_be_admin(AssignmentCreateView.as_view()),
         name='assignment-create-init'),
    path('assignment-edit/<int:pk>/<int:page>/', must_be_admin(AssignmentUpdateView.as_view()),
         name='assignment-edit'),

    path('du/seite<int:page>/', login_required(CleanerView.as_view()), name='cleaner'),
    path('du/', login_required(CleanerView.as_view()), name='cleaner-no-page'),
    path('du/dienst<int:assignment_pk>/', login_required(CleanerView.as_view()), name='cleaner-no-page-to-assignment'),
    path('du/kalender/', login_required(CleanerCalendarView.as_view()), name='cleaner-calendar'),
    path('putzer-analytics/', login_required(CleanerAnalyticsView.as_view()), name='cleaner-analytics'),
    path('putzer-analytics/p<int:cleaner_page>/', login_required(CleanerAnalyticsView.as_view()),
         name='cleaner-analytics-with-cleaner-page'),

    path('putzer/neu/', must_be_admin(CleanerNewView.as_view()), name='cleaner-new'),
    path('putzer/<int:pk>/', login_required(CleanerUpdateView.as_view()),
         name='cleaner-edit'),
    path('putzer/<int:pk>/p<int:cleaner_page>', login_required(CleanerUpdateView.as_view()),
         name='cleaner-edit-with-cleaner-page'),
    path('cleaner-delete/<int:pk>/', must_be_admin(CleanerDeleteView.as_view()), name='cleaner-delete'),

    path('cleaning-week-tasks/<int:pk>/<int:page>/', must_be_admin(TaskCreateView.as_view()),
         name='cleaning-week-tasks'),
    path('cleaning-week-edit/<int:pk>/<int:page>/', must_be_admin(CleaningWeekUpdateView.as_view()),
         name='cleaning-week-edit'),
    path('cleaning-week-delete/<int:pk>/<int:page>/', must_be_admin(CleaningWeekDeleteView.as_view()),
         name='cleaning-week-delete'),

    path('tauschen/<int:assignment_pk>/<int:page>', login_required(DutySwitchNewView.as_view()),
         name='dutyswitch-create'),
    path('tausch-bearbeiten/<int:dutyswitch_pk>/<int:page>', login_required(DutySwitchUpdateView.as_view()),
         name='dutyswitch-update'),
    path('tauschanfrage-akzeptieren/<int:pk>/<int:page>', login_required(DutySwitchAcceptView.as_view()),
         name='dutyswitch-accept'),
    path('tauschanfrage-akzeptieren/<int:pk>', login_required(DutySwitchAcceptView.as_view()),
         name='dutyswitch-accept-no-cleaner-page'),
    path('tauschanfrage-loeschen/<int:pk>/<int:page>', login_required(DutySwitchDeleteView.as_view()),
         name='dutyswitch-delete'),

    path('putzplan-liste/', login_required(ScheduleList.as_view()), name='schedule-list'),
    path('putzplan/<slug:slug>/ab<int:week>/druckansicht/', login_required(SchedulePrintView.as_view()),
         name='schedule-print-view'),
    # path('putzplan/<slug:slug>/seite<int:page>/<slug:highlight_slug>/', login_required(ScheduleView.as_view()),
    #      name='schedule-highlight'),
    path('putzplan/<slug:slug>/seite<int:page>/', login_required(ScheduleView.as_view()), name='schedule'),
    path('putzplan/<slug:slug>/analytics/', login_required(ScheduleAnalyticsView.as_view()),
         name='schedule-analystics-view'),
    path('putzplan/<slug:slug>/analytics/s<int:schedule_page>/', login_required(ScheduleAnalyticsView.as_view()),
         name='schedule-analystics-view-with-schedule-page'),
    path('putzplan/<slug:slug>/', login_required(ScheduleView.as_view()), name='schedule-no-page'),

    path('schedule-new/', must_be_admin(ScheduleNewView.as_view()), name='schedule-new'),
    path('schedule-edit/<int:pk>/', must_be_admin(ScheduleUpdateView.as_view()),
         name='schedule-edit'),
    path('schedule-delete/<int:pk>/', must_be_admin(ScheduleDeleteView.as_view()),
         name='schedule-delete'),
    path('schedule/<int:pk>/tasks/', must_be_admin(ScheduleTaskList.as_view()),
         name='schedule-task-list'),
    path('schedule/<int:pk>/tasks/new/', must_be_admin(TaskTemplateNewView.as_view()),
         name='schedule-task-new'),

    path('schedule-group-new/', must_be_admin(ScheduleGroupNewView.as_view()),
         name='schedule-group-new'),
    path('schedule-group-edit/<int:pk>/', must_be_admin(ScheduleGroupUpdateView.as_view()),
         name='schedule-group-edit'),
    path('schedule-group-delete/<int:pk>/', must_be_admin(ScheduleGroupDeleteView.as_view()),
         name='schedule-group-delete'),

    path('geputzt/<int:assignment_pk>/<int:task_pk>', login_required(TaskCleanedView.as_view()),
         name='task-cleaned'),
    path('task-edit/<int:pk>/', must_be_admin(TaskTemplateUpdateView.as_view()), name='task-edit'),
    path('task-delete/<int:pk>/', must_be_admin(TaskTemplateDeleteView.as_view()), name='task-delete'),

    path('api/', include((router.urls, 'webinterface'), namespace="api"))
]
