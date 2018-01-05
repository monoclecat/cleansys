from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from .views import *

from django.views.generic.base import RedirectView
import datetime


app_name = 'webinterface'
urlpatterns = [
    # url(r'^switch/(?P<duty_pk>[\d]+)/(?P<old_cleaner_pk>[\d]+)/$',
    #    DutySwitchView.as_view(), name='switch-duty'),
]