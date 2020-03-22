from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from django.contrib.auth.forms import AuthenticationForm


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        exclude = ('slug',)
        labels = {
            'name': "Name des Putzplans",
            'cleaners_per_date': "Anzahl der Putzer pro Woche",
            'weekday': "Wochentag, an dem sich der Dienst wiederholen soll.",
            'frequency': "Häufigkeit der Putzdienste",
            'disabled': "Putzplan deaktivieren"
        }
        help_texts = {
            'weekday': "Dieser Wochentag sagt noch nichts darüber aus, wie viel Zeit die Putzer zum "
                       "Erledigen des Dienstes haben.",
        }

    schedule_group = forms. \
        ModelMultipleChoiceField(queryset=ScheduleGroup.objects.enabled(), label="Zugehörigkeit zur Putzgruppe",
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

        if kwargs['instance']:
            self.helper.layout.fields.insert(-1, HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:schedule-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Putzplan</a>"))


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
        self.helper = FormHelper()
        self.fields['schedules'].required = False
        self.helper.layout = Layout(
            'name',
            'schedules',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
            'disabled'
        )


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        fields = ['name', 'preference']
        labels = {
            'name': "Name des Putzers",
            'preference': "Putzvorlieben",
            'slack_id': "Wähle das Slackprofil des Putzers aus"
        }
        help_texts = {
            'slack_id': "Das Putzplan-System muss dafür mit dem Slack-Server verbunden sein."
        }

    email = forms.EmailField(label="Email des Putzers")

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
        else:
            # We are in the CreateView
            self.helper.layout.fields.insert(
                -1,
                HTML("<p>Bitte beachten: Der Putzer, den du jetzt erstellst, "
                     "wird zunächst unter \"ausgezogen\" aufgelistet sein. </p>"
                     "<p>Um den Putzer zu \"aktivieren\", muss zunächst seine Zugehörigkeit festgelegt werden."
                     "Das entsprechende Interface findest du im Reiter rechts vom Putzername unter "
                     "'<span class=\"glyphicon glyphicon-home\"></span> Zugehörigkeiten'.</p>"),
            )

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:cleaner-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Putzer</a>"))


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

            self.fields['beginning'].initial = kwargs['instance'].beginning_as_date
            self.fields['end'].initial = kwargs['instance'].end_as_date
            self.helper.layout.fields.insert(0, HTML("<h3>" + str(kwargs['instance'].group) + "</h3>"))
            if self.cleaner:
                self.helper.layout.fields.append(
                    HTML("<a class=\"btn btn-warning\" href=\"{% url \'webinterface:affiliation-list\' "
                         + str(self.cleaner.pk) + " %}\" "
                                                  "role=\"button\"><span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a>"))

        if kwargs['instance']:
            self.helper.layout.fields.append(HTML(
                "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                "href=\"{% url 'webinterface:affiliation-delete' object.pk %}\""
                "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> Lösche Zugehörigkeit</a>"))


class CleaningWeekForm(forms.ModelForm):
    class Meta:
        model = CleaningWeek
        fields = ['disabled']
        labels = {
            'disabled': "Putzdienst für diese Woche deaktivieren",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            cleaning_week = kwargs['instance']

            self.helper = FormHelper()
            self.helper.layout = Layout(
                HTML("<div class=\"alert alert-info\" role=\"alert\">Du bearbeitest die Woche von <b>{}</b> bis "
                     "<b>{}</b> für <b>{}</b></div>".format(cleaning_week.week_start(), cleaning_week.week_end(),
                                                            cleaning_week.schedule, cleaning_week.schedule.name)),
                'disabled',
                HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                     "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
            )


class AssignmentCreateForm(forms.Form):
    from_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Die Kalenderwoche von TT.MM.YYYY")
    to_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Die Kalenderwoche bis TT.MM.YYYY")

    # See definitions in model Schedule, method create_assignments_over_timespan()
    mode = forms.ChoiceField(choices=[(3, 'Bestehende Putzdienste komplett löschen und neu generieren.'),
                                      (2, 'Behalte vorhandene Putzdienste behalten und nur dort Putzdienste '
                                          'erzeugen wo welche fehlen.')],
                             widget=forms.RadioSelect, label="Modus")

    def __init__(self, initial_begin=None, initial_end=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if initial_begin:
            self.fields['from_date'].initial = epoch_week_to_monday(initial_begin)

        if initial_end:
            self.fields['to_date'].initial = epoch_week_to_sunday(initial_end)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'from_date',
            'to_date',
            'mode',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:schedule-view\' schedule.slug page %}\" "
                 "role=\"button\"><span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a>")
        )


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['cleaner']
        labels = {
            'cleaner': "Putzer für diesen Putzdienst",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            assignment = kwargs['instance']

            self.helper = FormHelper()
            self.helper.layout = Layout(
                HTML("<div class=\"alert alert-info\" role=\"alert\">Du bearbeitest einen einzelnen Putzdienst "
                     "im Putzplan <b>{}</b> in der Woche von <b>{}</b> bis <b>{}</b></div>".
                     format(assignment.schedule, assignment.cleaning_week.week_start(),
                            assignment.cleaning_week.week_end())),
                'cleaner',
                HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                     "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
            )


class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        fields = '__all__'
        labels = {
            'task_name': "Name der Aufgabe",
            'start_days_before': "Kann ab diesem Wochentag angefangen werden",
            'end_days_after': "Darf bis zu diesem Wochentag gemacht werden",
            'task_help_text': "Hilfetext",
            'task_disabled': "Aufgabe deaktiviert"
        }
        help_texts = {
            'task_help_text': "Gib dem Putzer Tipps, um die Aufgabe schnell und effektiv machen zu können."
        }
        widgets = {
            'task_help_text': forms.Textarea
        }

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

        days_before = [(i, "{} - {} Tage davor".format(Schedule.WEEKDAYS[(schedule.weekday - i) % 7][1], i))
                       for i in range(0, 7)]
        days_after = [(i, "{} - {} Tage danach".format(Schedule.WEEKDAYS[(schedule.weekday + i) % 7][1], i))
                      for i in range(0, 7)]

        self.fields['start_days_before'].choices = days_before
        self.fields['end_days_after'].choices = days_after
        self.helper.layout.fields.append(
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:schedule-task-list\' +" + str(schedule.pk) + " %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "))


class TaskCreateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("{% include \"webinterface_snippets/list_of_task_have_vs_dont_haves_for_cleaningweek.html\" %}"),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Fehlende Aufgaben erstellen</button> "),
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:schedule-view\' cleaning_week.schedule.slug page %}\" "
                 "role=\"button\"><span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a>")
        )


class TaskCleanedForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['cleaned_by']
        labels = {
            'cleaned_by': "Putzer, der diese Aufgabe erledigt hat",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'instance' in kwargs and kwargs['instance']:
            self.fields['cleaned_by'].queryset = kwargs['instance'].possible_cleaners()
            self.fields['cleaned_by'].required = False
            self.helper = FormHelper()
            self.helper.layout = Layout(
                HTML("<h4>Hilfetext</h4>"),
                HTML("<p>{{ help_text }}</p>"),
                'cleaned_by',
                HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                     "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "),
                HTML("<a class=\"btn btn-warning\" "
                     "href=\"{% url \'webinterface:assignment-tasks\' assignment.pk %}\" "
                     "role=\"button\"><span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a>")
            )


class DutySwitchCreateForm(forms.ModelForm):
    class Meta:
        model = DutySwitch
        exclude = ('acceptor_assignment',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<div class=\"alert alert-info\" role=\"alert\">Du möchtest deinen Putzdienst "
                 "im Putzplan <b>{{ assignment.schedule }}</b> in der Woche von "
                 "<b>{{ assignment.cleaning_week.week_start|date:\"d. M Y\" }}</b> bis "
                 "<b>{{ assignment.cleaning_week.week_end|date:\"d. M Y\" }}</b> "
                 "tauschen.</div>"),
            HTML("<p>Wenn du den Putzdienst-Tausch in Auftrag gibst, werden Putzdienste in der Zukunft gesucht "
                 "während denen du keinen Urlaub angemeldet hast. Die Putzer dieser Tausch-Kandidaten werden "
                 "benachrichtigt und gefragt, ob sie mit dir tauschen möchten.</p>"),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\" "
                 "style=\"white-space: normal; margin: 0.5em\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> "
                 "Ja, ich möchte den Putzdienst-Tausch in Auftrag geben.</button> "),
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:cleaner\' page %}\" role=\"button\" "
                 "style=\"white-space: normal; margin: 0.5em\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Nein, hol mich hier raus!</a> ")
        )


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

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<div class=\"alert alert-info\" role=\"alert\"><b>{{ dutyswitch.requester_assignment.cleaner }}</b> "
                 "möchte seinen Putzdienst am "
                 "<b>{{ dutyswitch.requester_assignment.assignment_date }}</b> tauschen</div>"),
            'acceptor_assignment',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\" "
                 "style=\"white-space: normal; margin: 0.5em\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> "
                 "Ja, ich nehme den Tausch an.</button> "),
            HTML("<a class=\"btn btn-warning\" "
                 "href=\"{% url \'webinterface:cleaner\' page %}\" role=\"button\" "
                 "style=\"white-space: normal; margin: 0.5em\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> ")
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
