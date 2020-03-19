from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from slackbot.slackbot import get_slack_users, slack_running
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

import re

pv_email = re.compile("(\S+)\.(\S+)@pvka\.de")


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        exclude = ('slug',)

    name = forms.CharField(max_length=20, label="Putzplan Name", help_text="Der Name des Putzplans",
                           required=True, widget=forms.TextInput)

    cleaners_per_date = forms.ChoiceField(choices=Schedule.CLEANERS_PER_DATE_CHOICES,
                                          label="Anzahl der Putzer pro Woche",
                                          help_text="Z.B. Bad braucht nur einen, Bar braucht zwei.",
                                          required=True, initial=1)

    weekday = forms.ChoiceField(choices=Schedule.WEEKDAYS, required=True, initial=6,
                                label="Wochentag, an dem sich der Dienst wiederholen soll.",
                                help_text="Normale Putzdienste wiederholen sich immer Sonntags, Mülldienste sind "
                                          "i.d.R. unter der Woche. Dieser Wochentag sagt noch nichts darüber aus, "
                                          "wie viel Zeit die Putzer zum Erledigen des Dienstes haben.")

    frequency = forms.ChoiceField(choices=Schedule.FREQUENCY_CHOICES, required=True, initial=1,
                                  label="Häufigkeit der Putzdienste",
                                  help_text="Wenn du zwei Putzdienste hast, die alle zwei Wochen dran sind, "
                                            "aber nicht an gleichen Tagen, dann wähle bei einem 'Gerade Wochen' und "
                                            "beim anderen 'Ungerade Wochen' aus.")

    schedule_group = forms. \
        ModelMultipleChoiceField(queryset=ScheduleGroup.objects.enabled(),
                                 widget=forms.CheckboxSelectMultiple,
                                 label="Zugehörigkeit", required=False,
                                 help_text="Wähle die Gruppe(n), zu der/denen der Putzplan gehört.")

    disabled = forms.BooleanField(label="Deaktivieren", required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            initial['schedule_group'] = ScheduleGroup.objects.filter(schedules=kwargs['instance'])
            kwargs['initial'] = initial

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            'name',
            'weekday',
            'cleaners_per_date',
            'frequency',
            'schedule_group',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
            'disabled',
        )

        if 'instance' in kwargs and kwargs['instance']:
            self.fields['frequency'].disabled = True
            self.fields['cleaners_per_date'].disabled = True
            self.fields['weekday'].disabled = True


class ScheduleGroupForm(forms.ModelForm):
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

    disabled = forms.BooleanField(required=False, label="Deaktivieren")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            'name',
            'schedules',
            'disabled',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
        )


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        exclude = ('slug', 'user', 'time_zone')

    name = forms.CharField(max_length=20, label="Name des Putzers", widget=forms.TextInput)

    email = forms.EmailField(label="Email des Putzers")

    preference = forms.ChoiceField(choices=Cleaner.PREFERENCE, initial=2, label="Putzvorlieben")

    slack_id = forms.ChoiceField(choices=(None, "--------------------"), label="Wähle des Putzers Slackprofil aus.",
                                 required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            kwargs['initial'] = initial

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'email',
            'preference',

            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
        )

        if 'instance' in kwargs and kwargs['instance']:
            # We are in the UpdateView
            self.fields['email'].initial = kwargs['instance'].user.email

        if slack_running():
            self.fields['slack_id'].choices = get_slack_users()
            self.helper.layout.fields.insert(5, 'slack_id')
        else:
            self.Meta.exclude += ('slack_id',)
            self.helper.layout.fields.insert(0, HTML("<p><i>Slack ist ausgeschaltet. Schalte Slack ein, um "
                                                     "dem Putzer eine Slack-ID zuordnen zu können.</i></p>"))

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:cleaner-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Putzer</a>"))


class CleanerNewForm(CleanerForm):
    schedule_group = forms.ModelChoiceField(
        queryset=ScheduleGroup.objects.enabled(), required=False, empty_label="---Ausgezogen---",
        label="Wähle die Putzplan-Gruppierung, zu der der/die Putzer/in gehört")
    schedule_group__beginning = forms.DateField(
        input_formats=['%d.%m.%Y'], required=False, label="Beginn der Zugehörigkeit TT.MM.YYYY")
    schedule_group__end = forms.DateField(
        input_formats=['%d.%m.%Y'], required=False, label="Ende der Zugehörigkeit TT.MM.YYYY")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'email',
            'preference',
            HTML("<p>Du erstellst einen neue/n Putzer/in. Bitte gebe den Zeitraum an, während dem er/sie "
                 "voraussichtlich Teil der Putzgemeinschaft sein wird. </p>"
                 "<p>Durch Klicken auf den Reiter rechts vom Putzername, dann auf "
                 "'<span class=\"glyphicon glyphicon-home\"></span> Zugehörigkeiten' können diese Daten bearbeitet"
                 "werden.</p>"),
            'schedule_group',
            'schedule_group__beginning',
            'schedule_group__end',

            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
        )

    def clean(self):
        cleaned_data = super().clean()

        schedule_group = cleaned_data.get("schedule_group")
        beginning = cleaned_data.get("schedule_group__beginning")
        end = cleaned_data.get("schedule_group__end")

        if schedule_group is not None and (beginning is None or end is None):
            raise ValidationError("Wenn eine Zugehörigkeit angegeben wird, muss sein Beginn und Ende "
                                  "ebenfalls angegeben werden.")


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
                     "Ein Putzer zählt als ausgezogen wenn seine Zugehörigkeiten ausgelaufen sind."
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
            Affiliation.date_validator(pk=pk, cleaner=self.cleaner, beginning=beginning, end=end)
        except TypeError:
            pass

        return cleaned_data

    def __init__(self, cleaner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleaner = cleaner
        if not self.cleaner and 'instance' in kwargs and kwargs['instance']:
            self.cleaner = kwargs['instance'].cleaner

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'beginning',
            'end',
            'group',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> ")
        )

        if self.cleaner and self.cleaner.is_active():
            self.fields['group'].initial = self.cleaner.current_affiliation().group

        if 'instance' in kwargs and kwargs['instance']:
            # We are in AffiliationUpdateView

            # if kwargs['instance'].beginning < timezone.now().date():
            #     self.fields['beginning'].disabled = True
            # if kwargs['instance'].end < timezone.now().date():
            #     self.fields['end'].disabled = True
            self.fields['beginning'].initial = kwargs['instance'].beginning_as_date
            self.fields['end'].initial = kwargs['instance'].end_as_date
            self.helper.layout.fields.insert(0, HTML("<h3>" + str(kwargs['instance'].group) + "</h3>"))
            if self.cleaner:
                self.helper.layout.fields.append(
                    HTML("<a class=\"btn btn-warning\" href=\"{% url \'webinterface:affiliation-list\' "
                         + str(self.cleaner.pk) + " %}\" "
                                                  "role=\"button\"><span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a>"))


class CleaningDayForm(forms.ModelForm):
    class Meta:
        model = CleaningWeek
        fields = ['disabled', 'date']

    disabled = forms.BooleanField(label="Putzdienst für diese Woche deaktivieren", required=False)

    date = forms.ChoiceField(label="Datum")

    def __init__(self, cleaning_day=None, schedule=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            cleaning_day = kwargs['instance']
            schedule = cleaning_day.schedule

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<div class=\"alert alert-info\" role=\"alert\">Du bearbeitest den Putzdienst "
                 "für <b>{}</b> am <b>{}</b></div>".format(schedule.name, cleaning_day.date)),
            'disabled',
            'date',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
        )

        possible_dates = [cleaning_day.date + datetime.timedelta(days=x) for x in
                          range(-1*cleaning_day.date.weekday(), -1*cleaning_day.date.weekday() + 7)]

        self.fields['date'].choices = [(date, "{} - {}".format(Schedule.WEEKDAYS[date.weekday()][1], date))
                                       for date in possible_dates]
        self.fields['date'].initial = cleaning_day.date


class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        exclude = ('schedule',)

    task_name = forms.CharField(label="Name der Aufgabe")

    start_days_before = forms.ChoiceField(
        label="Kann ab diesem Wochentag angefangen werden",
    )

    end_days_after = forms.ChoiceField(
        label="Darf bis zu diesem Wochentag gemacht werden",
    )

    task_help_text = forms.CharField(
        widget=forms.Textarea,
        label="Hilfetext", help_text="Gib dem Putzer Tipps, um die Aufgabe schnell und effektiv machen zu können."
    )

    task_disabled = forms.BooleanField(label="Deaktiviert", required=False)

    def clean(self):
        cleaned_data = super().clean()

        task_name = cleaned_data.get('task_name')
        start_days_before = cleaned_data.get('start_days_before')
        end_days_after = cleaned_data.get('end_days_after')

        if task_name and not start_days_before or task_name and not end_days_after:
            raise forms.ValidationError('Zu einer neuen Aufgabe müssen die Tage festgelegt sein, ab wann und bis wann '
                                        'die Aufgabe erledigt werden kann!', code='incomplete_inputs')
        if start_days_before + end_days_after > 6:
            raise forms.ValidationError('Die Zeitspanne, in der die Aufgabe gemacht werden kann, darf '
                                        'nicht eine Woche oder mehr umfassen!', code='span_gt_one_week')

        return cleaned_data

    def __init__(self, schedule=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            schedule = kwargs['instance'].schedule

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'task_name',
            HTML("<div class=\"alert alert-info\" role=\"alert\">Diese Aufgabe gehört zum Putzplan "
                 "<b>{}</b>, welcher sich jeden <b>{}</b> wiederholt</div>".format(
                    schedule.name,
                    Schedule.WEEKDAYS[schedule.weekday][1])),
            'start_days_before',
            'end_days_after',
            'task_help_text',
            'task_disabled',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
        )

        self.fields['start_days_before'].initial = 0
        self.fields['end_days_after'].initial = 0

        days_before = [(i, "{} - {} Tage davor".format(Schedule.WEEKDAYS[(i + schedule.weekday) % 7][1], i))
                       for i in range(6, -1, -1)]
        days_after = [(i, "{} - {} Tage danach".format(Schedule.WEEKDAYS[(i + schedule.weekday) % 7][1], i))
                      for i in range(0, 7)]

        self.fields['start_days_before'].choices = days_before
        self.fields['end_days_after'].choices = days_after
        self.helper.layout.fields.append(
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:schedule-task-list\' +" + str(schedule.pk) + " %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "))


class AssignmentCleaningForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ('cleaners_comment',)

    cleaners_comment = forms.CharField(widget=forms.Textarea, max_length=200,
                                       label="Kommentare, Auffälligkeiten, ... (speichern nicht vergessen)",
                                       help_text="Max. 200 Zeichen",
                                       required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Div('cleaners_comment'),
            Submit('save_comment', 'Kommentar speichern', css_class="btn btn-block"),
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


class ResultsForm(forms.Form):
    start_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Von TT.MM.YYYY")
    end_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Bis TT.MM.YYYY")

    # show_deviations = forms.BooleanField(widget=forms.CheckboxInput, required=False,
    #                                      label="Show average absolute deviations (not really important)")

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})

        start_date = timezone.now().date() - datetime.timedelta(days=30)
        end_date = start_date + datetime.timedelta(days=3 * 30)
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
