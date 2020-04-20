from django.apps import AppConfig


class WebinterfaceConfig(AppConfig):
    name = 'webinterface'

    def ready(self):
        from webinterface.signals import schedule_group_changed, send_email__new_acceptable_dutyswitch
