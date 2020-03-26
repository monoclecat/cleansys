from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from django.contrib.auth.forms import AuthenticationForm


def html_alert_banner(content: str, alert_level='info'):
    return HTML("<div class=\"alert alert-{}\" role=\"alert\">{}</div>".format(alert_level, content))


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['name', 'weekday', 'cleaners_per_date', 'frequency', 'disabled']
        labels = {
            'name': "Name des Putzplans",
            'weekday': "Wochentag, an dem sich der Dienst wiederholen soll.",
            'cleaners_per_date': "Anzahl der Putzer pro Woche (Warnung beachten!)",
            'frequency': "Häufigkeit der Putzdienste (Warnung beachten!)",
            'disabled': "Putzplan deaktivieren"
        }
        help_texts = {
            'weekday': "Dieser Wochentag sagt noch nichts darüber aus, wie viel Zeit die Putzer zum "
                       "Erledigen des Dienstes haben.",
            'cleaners_per_date': "<b>Achtung! Nicht leichtfertig ändern!</b> Wenn die Anzahl an Putzern pro Woche "
                                 "geändert wird, müssen alle zukünftigen Putzdienste neu verteilt werden!",
            'frequency': "<b>Achtung! Nicht leichtfertig ändern!</b> Wenn die Häufigkeit des Putzdienstes "
                         "geändert wird, müssen alle zukünftigen Putzdienste neu verteilt werden!"
        }

    schedule_group = forms. \
        ModelMultipleChoiceField(queryset=ScheduleGroup.objects.enabled(),
                                 label="Zugehörigkeit zu Putzgruppen (mehrere möglich)",
                                 help_text="Alle Putzer einer Putzgruppe sind allen Putzplänen dieser "
                                           "Gruppe zugewiesen. Ein Putzer kann nur einer Putzgruppe auf "
                                           "einmal zugewiesen sein. Ein Putzplan kann jedoch mehreren Putzgruppen "
                                           "angehören.",
                                 widget=forms.CheckboxSelectMultiple,
                                 required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            initial['schedule_group'] = ScheduleGroup.objects.filter(schedules=kwargs['instance'])
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)


class ScheduleGroupForm(forms.ModelForm):
    class Meta:
        model = ScheduleGroup
        fields = '__all__'
        labels = {
            'name': "Name der Putzplan-Gruppe",
            'schedules': "Putzpläne, die dieser Putzplan-Gruppe angehören",
            'disabled': "Putzplan-Gruppierung deaktivieren"
        }
        help_texts = {
            'name': "Dieser Name steht z.B. für ein Geschoss oder eine bestimmte Sammlung an Putzplänen, "
                    "denen manche oder alle Bewohner angehören."
        }
        widgets = {
            'schedules': forms.CheckboxSelectMultiple
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['schedules'].required = False


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        fields = ['name', ]
        labels = {
            'name': "Name des Putzers",
            'slack_id': "Wähle das Slackprofil des Putzers aus"
        }
        help_texts = {
            'slack_id': "Das Putzplan-System muss dafür mit dem Slack-Server verbunden sein."
        }

    email = forms.EmailField(label="Email des Putzers")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            # We are in the UpdateView
            self.fields['email'].initial = kwargs['instance'].user.email


class AffiliationForm(forms.ModelForm):
    """
    AffiliationForm allows creating and editing Affiliation objects. Important to note is that the beginning and end
    fields of the model are integer fields that store the week number since 1.1.1970.
    Showing this number and expecting only such a number as an input is not very user-friendly, which is why
    this field displays the beginning_as_date() and end_as_date() values of the respective model fields.
    As an input, this form accepts dates and translates them into these so-called "epoch-weeks" using the
    function date_to_epoch_week().
    """
    class Meta:
        model = Affiliation
        fields = ['group']
        labels = {
            'group': "Zugehörigkeit"
        }
        help_texts = {
            'group': "Wähle die Etage oder die Gruppe, zu der der Putzer gehört. <br> "
                     "Ein Putzer zählt als ausgezogen wenn alle seine Zugehörigkeiten ausgelaufen sind."
        }

    beginning = forms.DateField(input_formats=['%d.%m.%Y'], required=True, label="Beginn der Zugehörigkeit TT.MM.YYYY",
                                help_text="Das eingegebene Datum wird auf den nächsten Montag abgerundet.")
    end = forms.DateField(input_formats=['%d.%m.%Y'], required=True, label="Ende der Zugehörigkeit TT.MM.YYYY",
                          help_text="Das eingegebene Datum wird auf den nächsten Sonntag aufgerundet.")

    def clean(self):
        cleaned_data = super().clean()

        pk = self.instance.pk
        try:
            beginning = date_to_epoch_week(cleaned_data.get('beginning'))
            end = date_to_epoch_week(cleaned_data.get('end'))
            Affiliation.date_validator(affiliation_pk=pk, cleaner=self.cleaner, beginning=beginning, end=end)
        except TypeError:
            pass

        return cleaned_data

    def __init__(self, cleaner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleaner = cleaner
        if not self.cleaner and 'instance' in kwargs and kwargs['instance']:
            self.cleaner = kwargs['instance'].cleaner

        if self.cleaner and self.cleaner.is_active():
            self.fields['group'].initial = self.cleaner.current_affiliation().group

        if 'instance' in kwargs and kwargs['instance']:
            # We are in AffiliationUpdateView
            self.fields['beginning'].initial = kwargs['instance'].beginning_as_date
            self.fields['end'].initial = kwargs['instance'].end_as_date


class CleaningWeekForm(forms.ModelForm):
    class Meta:
        model = CleaningWeek
        fields = ['disabled']
        labels = {
            'disabled': "Putzdienst für diese Woche deaktivieren",
        }


class AssignmentCreateForm(forms.Form):
    from_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Die Kalenderwoche von TT.MM.YYYY")
    to_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Die Kalenderwoche bis TT.MM.YYYY")

    schedules = forms.ModelMultipleChoiceField(queryset=Schedule.objects.enabled(), widget=forms.CheckboxSelectMultiple,
                                               label="Putzpläne, die im angegebenen Zeitraum bearbeitet werden sollen")

    def __init__(self, initial_begin=None, initial_end=None, initial_schedules=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if initial_schedules:
            self.fields['schedules'].initial = initial_schedules

        if initial_begin:
            self.fields['from_date'].initial = epoch_week_to_monday(initial_begin)

        if initial_end:
            self.fields['to_date'].initial = epoch_week_to_sunday(initial_end)

    def clean(self):
        cleaned_data = super().clean()
        max_time_frame = 52  # Weeks

        if cleaned_data['from_date'] and cleaned_data['to_date']:
            from_week = date_to_epoch_week(cleaned_data['from_date'])
            to_week = date_to_epoch_week(cleaned_data['to_date'])

            if to_week < from_week:
                raise forms.ValidationError("Die Kalenderwoche 'von' darf nicht nach der Kalenderwoche 'bis' liegen!")

            if to_week - from_week > max_time_frame:
                raise forms.ValidationError("Die angegebene Zeitspanne darf nicht "
                                            "mehr als {} Wochen betragen!".format(max_time_frame))
        return cleaned_data


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['cleaner']
        labels = {
            'cleaner': "Putzer für diesen Putzdienst",
        }


class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        fields = ['task_name', 'task_help_text', 'start_days_before', 'end_days_after', 'task_disabled']
        labels = {
            'task_name': "Name der Aufgabe",
            'start_days_before': "Kann ab diesem Wochentag angefangen werden",
            'end_days_after': "Darf bis zu diesem Wochentag gemacht werden",
            'task_help_text': "Hilfetext",
            'task_disabled': "Aufgabe deaktiviert (beachte Warnung!)"
        }
        help_texts = {
            'task_help_text': "Gib dem Putzer Tipps, um die Aufgabe schnell und effektiv machen zu können.",
            'task_disabled': "<b>Achtung!</b> Wenn dieser Wert geändert wird, müssen die Aufgaben aller zukünfigen "
                             "Putzdienste aktualisiert werden!"
        }
        widgets = {
            'task_help_text': forms.Textarea
        }

    def __init__(self, schedule=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            schedule = kwargs['instance'].schedule

        self.fields['start_days_before'].initial = 0
        self.fields['end_days_after'].initial = 0

        days_before = [(i, "{} - {} Tage davor".format(Schedule.WEEKDAYS[(schedule.weekday - i) % 7][1], i))
                       for i in range(0, 7)]
        days_after = [(i, "{} - {} Tage danach".format(Schedule.WEEKDAYS[(schedule.weekday + i) % 7][1], i))
                      for i in range(0, 7)]

        self.fields['start_days_before'].choices = days_before
        self.fields['end_days_after'].choices = days_after


class TaskCleanedForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['cleaned_by']
        labels = {
            'cleaned_by': "Putzer, der diese Aufgabe erledigt hat",
        }
        widgets = {
            'cleaned_by': forms.RadioSelect
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            self.fields['cleaned_by'].queryset = kwargs['instance'].possible_cleaners()
            self.fields['cleaned_by'].required = False


class DutySwitchCreateForm(forms.ModelForm):
    class Meta:
        model = DutySwitch
        exclude = ('acceptor_assignment',)


class DutySwitchAcceptForm(forms.ModelForm):
    class Meta:
        model = DutySwitch
        fields = ('acceptor_assignment',)
        labels = {
            'acceptor_assignment': "Welchen deiner Putzdienst möchtest du mit dem obigen tauschen?"
        }

    def __init__(self, cleaner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            self.fields['acceptor_assignment'].queryset = \
                cleaner.switchable_assignments_for_request(kwargs['instance']).order_by('cleaning_week__week')


class AuthFormWithSubmit(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'username' in request.GET and request.GET['username']:
            initial['username'] = request.GET['username']
        kwargs['initial'] = initial
        super().__init__(request, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password',
            Submit('login', 'Einloggen', css_class="btn btn-block"),
        )

        if 'username' in kwargs['initial']:
            self.fields['username'].disabled = True
