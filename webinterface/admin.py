from django.contrib import admin
from .models import *

admin.site.register(Cleaner)
admin.site.register(Schedule)
admin.site.register(ScheduleGroup)
