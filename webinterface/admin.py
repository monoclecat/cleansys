from django.contrib import admin
from .models import *

admin.site.register(Cleaner)
admin.site.register(CleaningSchedule)
admin.site.register(CleaningScheduleGroup)
