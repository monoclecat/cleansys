from django.core.management.base import BaseCommand
from webinterface.views import create_cleaner_analytics, create_schedule_analytics


class Command(BaseCommand):
    help = 'Creates plots for CleanerAnalyticsView and ScheduleAnalyticsView. This function is best run ' \
           'as a Cron job once a week. Creating the plots and saving them under media/ saves processing ' \
           'time, as collecting all the data from the database is very expensive. '

    def handle(self, *args, **options):
        create_cleaner_analytics(recreate=True)
        create_schedule_analytics(recreate=True)
