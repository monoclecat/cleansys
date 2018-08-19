from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from slackbot.slackbot import get_slack_users, slack_running
from django.contrib.auth.forms import AuthenticationForm


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Config
        fields = ('date_due', 'trust_in_users', 'starts_days_before_due', 'ends_days_after_due')

    date_due = forms.ChoiceField(choices=Config.WEEKDAYS, initial=6,
                                 label="Putztag: Wochentag, für den Putzdienste definiert sind.",
                                 help_text="Dies ist nicht der Wochetag, bis den die Putzdienste gemacht sein müssen!")
    trust_in_users = forms.BooleanField(required=False, label="Putzer können sich ohne Passwort einloggen.",
                                        help_text="Eine Änderung dieses Feldes hat weitreichende Konsequenzen.")

    starts_days_before_due = forms.IntegerField(
        label="Putzdienste können so viele Tag vor dem Putztag gemacht werden.")

    ends_days_after_due = forms.IntegerField(
        label="Putzdienste können so viele Tag nach dem Putztag gemacht werden.")

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'date_due', 'starts_days_before_due', 'ends_days_after_due',
            Fieldset('Login-Verhalten', 'trust_in_users'),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
        )


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


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ('cleaners_comment',)

    cleaners_comment = forms.CharField(widget=forms.Textarea, max_length=200,
                                       label="Kommentare, Auffälligkeiten, ... (speichern nicht vergessen)",
                                       help_text="Max. 200 Zeichen",
                                       required=False)

    def __init__(self, *args, **kwargs):
        super(AssignmentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Div('cleaners_comment'),
            Submit('save_comment', 'Kommentar speichern', css_class="btn btn-block"),
        )


class ResultsForm(forms.Form):
    start_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Von TT.MM.YYYY")
    end_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Bis TT.MM.YYYY")

    # show_deviations = forms.BooleanField(widget=forms.CheckboxInput, required=False,
    #                                      label="Show average absolute deviations (not really important)")

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})

        start_date = timezone.now().date() - datetime.timedelta(days=30)
        end_date = start_date + datetime.timedelta(days=3*30)
        initial['start_date'] = start_date.strftime('%d.%m.%Y')
        initial['end_date'] = end_date.strftime('%d.%m.%Y')

        kwargs['initial'] = initial

        super(ResultsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'start_date',
            'end_date',
            HTML(
                "<button class=\"btn btn-success\" type=\"submit\" name=\"save\" "
                "style=\"margin:0.5em 0.5em 0.5em 1em\">"
                "<span class=\"glyphicon glyphicon-chevron-right\"></span> Weiter</button> "),
            HTML("<br>"),
        )


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        exclude = ('slug', 'user', 'time_zone')

    name = forms.CharField(max_length=10, label="Name des Putzers", widget=forms.TextInput)

    schedule_group = forms.\
        ModelChoiceField(queryset=ScheduleGroup.objects.all(), widget=forms.RadioSelect,
                         label="Zugehörigkeit", help_text="Wähle die Etage oder die Gruppe, zu der der Putzer gehört.")

    schedule_group__action_date = forms.DateField(input_formats=['%d.%m.%Y'], required=True)

    preference = forms.ChoiceField(choices=Cleaner.PREFERENCE, initial=2, label="Putzvorlieben")

    slack_id = forms.ChoiceField(choices=(None, "--------------------"), label="Wähle des Putzers Slackprofil aus.",
                                 required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            kwargs['initial'] = initial

        super(CleanerForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'preference',
            Fieldset(
                'Einzug/Umzug/Auszug',
                'schedule_group',
                'schedule_group__action_date'),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
        )

        if 'instance' in kwargs and kwargs['instance']:
            # We are in the UpdateView
            self.fields['schedule_group'].empty_label = "---Ausgezogen---"
            self.fields['schedule_group'].required = False
            self.fields['schedule_group'].initial = kwargs['instance'].affiliation_set.first().group
            self.helper.layout.fields[2].insert(1, HTML('<p class="bg-danger">Bei Änderung der Zugehörigkeit muss '
                                                     'auch ein Datum angegeben werden!</p>'))
            self.fields['schedule_group__action_date'].required = False
            self.fields['schedule_group__action_date'].label = "Der Putzer zieht zum TT.MM.YYYY um bzw. aus."
        else:
            # We are in the CreateView
            self.fields['schedule_group'].empty_label = None
            self.fields['schedule_group__action_date'].label = "Der Putzer zieht zum TT.MM.YYYY ein."


        if slack_running():
            self.fields['slack_id'].choices = get_slack_users()
            self.helper.layout.fields.insert(5, 'slack_id')
        else:
            self.Meta.exclude += ('slack_id',)
            self.helper.layout.fields.insert(5, HTML("<p><i>Slack ist ausgeschaltet. Schalte Slack ein, um "
                                                     "dem Putzer eine Slack-ID zuordnen zu können.</i></p>"))

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:cleaner-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Putzer</a>"))


class CleaningScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        exclude = ('slug',)

    name = forms.CharField(max_length=20, label="Putzplan Name", help_text="Der Name des Putzplans",
                           required=True, widget=forms.TextInput)

    cleaners_per_date = forms.ChoiceField(choices=Schedule.CLEANERS_PER_DATE_CHOICES,
                                          label="Anzahl der Putzer pro Woche",
                                          help_text="Z.B. Bad braucht nur einen, Bar braucht zwei.",
                                          required=True, initial=1)

    frequency = forms.ChoiceField(choices=Schedule.FREQUENCY_CHOICES, required=True, initial=1,
                                  label="Häufigkeit der Putzdienste",
                                  help_text="Wenn du zwei Putzdienste hast, die alle zwei Wochen dran sind, "
                                            "aber nicht an gleichen Tagen, dann wähle bei einem 'Gerade Wochen' und "
                                            "beim anderen 'Ungerade Wochen' aus.")

    schedule_group = forms. \
        ModelMultipleChoiceField(queryset=ScheduleGroup.objects.all(),
                                 widget=forms.CheckboxSelectMultiple,
                                 label="Zugehörigkeit", required=False,
                                 help_text="Wähle die Gruppe, zu der der Putzplan gehört.")

    tasks = forms.CharField(max_length=200, required=False, widget=forms.TextInput, label="Aufgaben des Putzdienstes",
                            help_text="Trage hier die Aufgaben mit Komma getrennt ein. Aus Kosmetischen Gründen "
                                      "empfehle ich dir, vor und nach dem Komma kein Leerzeichen zu lassen, also so: "
                                      "Herd,Ofen,Oberflächen")

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            initial['schedule_group'] = ScheduleGroup.objects.filter(schedules=kwargs['instance'])
            kwargs['initial'] = initial

        super(CleaningScheduleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            'name',
            'cleaners_per_date',
            'frequency',
            'schedule_group',
            'tasks',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
        )

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:cleaning-schedule-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Putzplan</a>"))


class CleaningScheduleGroupForm(forms.ModelForm):
    class Meta:
        model = ScheduleGroup
        fields = '__all__'

    name = forms.CharField(max_length=30, label="Name der Putzplan-Gruppe",
                           help_text="Dieser Name steht für ein Geschoss oder eine bestimmte Sammlung an Putzplänen, "
                                     "denen manche Bewohner angehören. Wenn du Putzer oder Pläne dieser Gruppe "
                                     "hinzufügen möchtest, so tue dies in den entsprechenden Putzer- und "
                                     "Putzplan-Änderungsformularen selbst. ",
                           required=True, widget=forms.TextInput)

    schedules = forms. \
        ModelMultipleChoiceField(queryset=Schedule.objects.all(),
                                 widget=forms.CheckboxSelectMultiple,
                                 label="Putzpläne", required=False,
                                 help_text="Wähle die Putzpläne, die dieser Gruppe angehören.")

    def __init__(self, *args, **kwargs):
        super(CleaningScheduleGroupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            'name',
            'schedules',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
        )

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:cleaning-schedule-group-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> "
                "Lösche Putzplan-Gruppierung</a>"))





