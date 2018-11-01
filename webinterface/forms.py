from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from slackbot.slackbot import get_slack_users, slack_running
from django.contrib.auth.forms import AuthenticationForm

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

    frequency = forms.ChoiceField(choices=Schedule.FREQUENCY_CHOICES, required=True, initial=1,
                                  label="Häufigkeit der Putzdienste",
                                  help_text="Wenn du zwei Putzdienste hast, die alle zwei Wochen dran sind, "
                                            "aber nicht an gleichen Tagen, dann wähle bei einem 'Gerade Wochen' und "
                                            "beim anderen 'Ungerade Wochen' aus.")

    schedule_group = forms. \
        ModelMultipleChoiceField(queryset=ScheduleGroup.objects.enabled(),
                                 widget=forms.CheckboxSelectMultiple,
                                 label="Zugehörigkeit", required=False,
                                 help_text="Wähle die Gruppe, zu der der Putzplan gehört.")

    disabled = forms.BooleanField(label="Deaktivieren", required=False)

    task_name = forms.CharField(max_length=20, label="Name der Aufgabe", required=False)

    task_start_days_before = forms.IntegerField(
        required=False, initial=1, label="Kann bis so viele Tage vor dem gelisteten Tag gamacht werden.",
        help_text="Bei Putzdiensten, die immer für Sonntag gelistet sind, würde eine 1 bedeuten, "
                  "dass der Putzdienst ab Samstag gemacht werden kann")
    task_end_days_after = forms.IntegerField(
        required=False, initial=2, label="Kann bis so viele Tage nach dem gelisteten Tag gamacht werden.",
        help_text="Bei Putzdiensten, die immer für Sonntag gelistet sind, würde eine 2 bedeuten, "
                  "dass der Putzdienst bis Dienstag gemacht werden kann")
    # TODO sum of both can't be more than 6

    def clean(self):
        cleaned_data = super().clean()

        task_name = cleaned_data.get('task_name')
        task_start_days_before = cleaned_data.get('task_start_days_before')
        task_end_days_after = cleaned_data.get('task_end_days_after')

        if task_name and not task_start_days_before or task_name and not task_end_days_after:
            raise forms.ValidationError('Zu einer neuen Aufgabe müssen die Tage festgelegt sein, ab wann und bis wann '
                                        'die Aufgabe erledigt werden kann!')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'instance' in kwargs and kwargs['instance']:
            initial['schedule_group'] = ScheduleGroup.objects.filter(schedules=kwargs['instance'])
            kwargs['initial'] = initial

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            'name',
            'cleaners_per_date',
            'frequency',
            'schedule_group',
            Accordion(
                HTML('<h3>Aufgaben</h3>'),
                AccordionGroup(
                    '--- Neue Aufgabe erstellen ---',
                    'task_name',
                    'task_start_days_before',
                    'task_end_days_after'
                ),
            ),
            'disabled',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 # TODO Add a save-and-keep-editing button or put it in Neue Aufgabe erstellen AccordionGroup
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
        )

        if 'instance' in kwargs and kwargs['instance']:
            self.fields['frequency'].disabled = True
            self.fields['cleaners_per_date'].disabled = True
            for task in kwargs['instance'].tasktemplate_set.all():
                self.helper.layout.fields[4].append(
                    AccordionGroup(
                        task.name,
                        HTML("<a class=\"btn btn-info\" href=\"{% url \'webinterface:task-edit\' "
                             +str(task.pk)+" %}\" role=\"button\">"
                             "<span class=\"glyphicon glyphicon-cog\"></span> Bearbeiten</a> "),
                    ),
                )
        else:
            self.helper.layout.fields[4][1] = HTML('Aufgaben können erst nach dem Speichern erstellt werden.')


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

    email = forms.EmailField(label="Email des Putzers in der Form vorname.nachname@pvka.de")

    schedule_group = forms.ModelChoiceField(queryset=ScheduleGroup.objects.enabled(),
                         label="Zugehörigkeit", help_text="Wähle die Etage oder die Gruppe, zu der der Putzer gehört.")

    schedule_group__action_date = forms.DateField(input_formats=['%d.%m.%Y'], required=True)

    preference = forms.ChoiceField(choices=Cleaner.PREFERENCE, initial=2, label="Putzvorlieben")

    slack_id = forms.ChoiceField(choices=(None, "--------------------"), label="Wähle des Putzers Slackprofil aus.",
                                 required=False)

    def clean(self):
        cleaned_data = super().clean()

        if pv_email.match(cleaned_data.get('email')) is None:
            raise forms.ValidationError("Ungültige Email! Sie muss wie folgt aussehen: vorname.nachname@pvka.de")

        schedule_group__action_date = cleaned_data.get('schedule_group__action_date')
        schedule_group = cleaned_data.get('schedule_group')
        queryset = Cleaner.objects.filter(name=cleaned_data['name'])
        if queryset.exists():
            # We are in the UpdateView
            cleaner = queryset.first()

            if cleaner.is_active() and cleaner.current_affiliation().group != schedule_group:
                if not schedule_group__action_date:
                    raise forms.ValidationError("Zur neuen Zugehörigkeit muss auch ein Datum angegeben werden!",
                                                code='new_aff_no_date')
                if schedule_group__action_date < cleaner.current_affiliation().beginning:
                    raise forms.ValidationError("Der Beginn der neuen Zugehörigkeit kann nicht vor dem "
                                                "Beginn der alten Zugehörigkeit liegen!",
                                                code='new_aff_before_old_aff')
        return cleaned_data

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
            Accordion(
                AccordionGroup(
                    'Zugehörigkeit',
                    HTML('<p class="bg-warning">Wenn sich nichts ändert, '
                         'bitte auch hier nichts ändern oder eingeben.</p>'),
                    'schedule_group',
                    'schedule_group__action_date'
                ),
            ),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
        )

        if 'instance' in kwargs and kwargs['instance']:
            # We are in the UpdateView
            self.fields['email'].initial = kwargs['instance'].user.email
            self.fields['schedule_group'].empty_label = "---Ausgezogen---"
            self.fields['schedule_group'].required = False
            if kwargs['instance'].is_active():
                self.fields['schedule_group'].initial = kwargs['instance'].current_affiliation().group
            self.fields['schedule_group__action_date'].required = False
            self.fields['schedule_group__action_date'].label = "Der Putzer zieht zum TT.MM.YYYY um bzw. aus."

            for affiliation in kwargs['instance'].affiliation_set.all():
                # TODO Mark each interval between Affiliations in warning color in which Cleaner was not living on the house
                if affiliation.beginning < timezone.now().date() and affiliation.end < timezone.now().date():
                    edit_button = HTML(
                        '<a class=\"btn btn-info\" role=\"button\" disabled="disabled">'
                        '<span class=\"glyphicon glyphicon-cog\"></span> Bearbeiten</a>')
                else:
                    edit_button = HTML(
                        '<a class=\"btn btn-info\" href=\"{% url \'webinterface:affiliation-edit\' '
                        +str(affiliation.pk)+' %}\" role=\"button\">'
                        '<span class=\"glyphicon glyphicon-cog\"></span> Bearbeiten</a>')
                group_name = str(affiliation.group) if affiliation.group else "Keine Gruppe"
                self.helper.layout.fields[3].append(
                    AccordionGroup(
                        group_name+' - '+str(affiliation.beginning.strftime('%d-%b-%Y'))+
                        ' bis '+str(affiliation.end.strftime('%d-%b-%Y')), edit_button)
                )
        else:
            # We are in the CreateView
            self.fields['schedule_group'].empty_label = None
            self.fields['schedule_group__action_date'].label = "Der Putzer zieht zum TT.MM.YYYY ein."


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


class AffiliationForm(forms.ModelForm):
    class Meta:
        model = Affiliation
        exclude = ('cleaner', 'group')

    beginning = forms.DateField(input_formats=['%d.%m.%Y'], required=True, label="Beginn der Zugehörigkeit")
    end = forms.DateField(input_formats=['%d.%m.%Y'], required=True, label="Ende der Zugehörigkeit")

    def clean(self):
        cleaned_data = super().clean()
        beginning = cleaned_data['beginning']
        end = cleaned_data['end']
        if beginning > end:
            raise forms.ValidationError("Das Ende darf nicht vor dem Beginn liegen!", code='end_before_beginning')
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'beginning',
            'end',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:cleaner-edit\' object.cleaner.pk %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "
                 )
        )

        # TODO to help prevent trying to set end after another's beginning, show max date that is allowed

        if 'instance' in kwargs and kwargs['instance']:
            if kwargs['instance'].beginning < timezone.now().date():
                self.fields['beginning'].disabled = True
            if kwargs['instance'].end < timezone.now().date():
                self.fields['end'].disabled = True

            self.helper.layout.fields.insert(0, HTML("<h3>"+str(kwargs['instance'].group)+"</h3>"))


class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        exclude = ('schedule',)

    name = forms.CharField(max_length=20, label="Name der Aufgabe")

    start_days_before = forms.IntegerField(required=False,
                                           label="Kann bis so viele Tage vor dem gelisteten Tag gamacht werden.",
                                           help_text="Bei Putzdiensten, die immer für Sonntag gelistet sind, würde "
                                                     "eine 1 bedeuten, dass der Putzdienst ab Samstag gemacht "
                                                     "werden kann")
    end_days_after = forms.IntegerField(required=False, initial=1,
                                        label="Kann bis so viele Tage nach dem gelisteten Tag gamacht werden.",
                                        help_text="Bei Putzdiensten, die immer für Sonntag gelistet sind, würde "
                                                  "eine 2 bedeuten, dass der Putzdienst bis Dienstag gemacht "
                                                  "werden kann")

    help_text = forms.CharField(required=False, widget=forms.Textarea, max_length=100,
                                label="Hilfetext", help_text="Gib dem Putzer Tipps, um die Aufgabe schnell und "
                                                             "effektiv machen zu können.")

    disabled = forms.BooleanField(label="Deaktiviert", required=False)

    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get('name')
        start_days_before = cleaned_data.get('start_days_before')
        end_days_after = cleaned_data.get('end_days_after')

        if name and not start_days_before or name and not end_days_after:
            raise forms.ValidationError('Zu einer neuen Aufgabe müssen die Tage festgelegt sein, ab wann und bis wann '
                                        'die Aufgabe erledigt werden kann!', code='incomplete_inputs')
        if start_days_before + end_days_after > 6:
            raise forms.ValidationError('Die Zeitspanne, in der die Aufgabe gemacht werden kann, darf '
                                        'nicht eine Woche oder mehr umfassen!', code='span_gt_one_week')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'start_days_before',
            'end_days_after',
            'help_text',
            'disabled',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:schedule-edit\' object.schedule.pk %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "
                 )
        )


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



















