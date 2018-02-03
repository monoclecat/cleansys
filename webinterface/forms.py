from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from slackbot.slackbot import get_slack_users, slack_running
from django.contrib.auth.forms import AuthenticationForm


class ComplaintReactForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ('status', 'comment_of_target')

    status = forms.ChoiceField(label="Welche Position nimmst du ein?",
                               choices=((1, '#1: Ich gestehe meinen Fehler ein und habe die Aufgabe nochmal geputzt. '
                                            'Es ist jetzt sauber!'),
                                        (2, '#2: Was soll das?!? Ich habe das richtig geputzt! Es sollen alle Putzer '
                                            'dieses Dienstes abstimmen, ob ich das richtig gemacht habe. Wenn mehr '
                                            'als die Hälfte meinen, ich habe meine Arbeit nicht richtig gemacht, '
                                            'werde ich eine Strafe akzeptieren. Das ist Demokratie.')),
                               widget=forms.RadioSelect)

    comment_of_target = forms.CharField(widget=forms.TextInput, max_length=50,
                                        label="Bitte äußere dich zu der Anschuldigung",
                                        help_text="Max. 50 Zeichen")

    def __init__(self, *args, **kwargs):
        print(kwargs)
        super(ComplaintReactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(HTML('<h4>Deine Mitputzer meinen, du hättest <span class="badge">{{ complaint.schedule.name }} -> '
                     '{{ complaint.task.name }} </span> nicht richtig gemacht!')),
            Div(HTML('<h4>Kommentare zur Beschwerde: <br><i>{{ complaint.comment }}</i>')),
            Div(HTML("<h4>Du musst spätestens <b>{{ complaint.react_until }}</b> geantwortet haben, "
                     "sonst nehmen wir an, dass du Position #2 einnimmst!</h4>"), css_class="well"),
            'status',
            'comment_of_target',
            HTML("<button class=\"btn btn-primary\" type=\"submit\" name=\"save\" style=\"margin: 0.5em\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Auf Beschwerde antworten.</button> "
                 "<input action=\"action\" type=\"button\" value=\"Zurück\" class=\"btn btn-default\" "
                 "style=\"margin: 0.5em\" onclick=\"window.history.go(-1); return false;\" />"),
        )


class ComplaintVoteForm(forms.Form):

    answer = forms.ChoiceField(label="Stimmt das?", choices=((1, 'Ja'), (2, 'Nein')), widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            self.object = kwargs['instance']
            kwargs.pop('instance')
        super(ComplaintVoteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h4>Der Putzer von '
                 '<span class="badge">{{ complaint.schedule.name }} -> {{ complaint.task.name }}</span> '
                 'wird beschuldigt, seine Aufgabe nicht richtig gemacht zu haben. </h4>'
                 '<p>Der beschuldigte Putzer hat sich zu der Anschuldigung wie folgt geäußert: <br> '
                 '{{ complaint.comment_of_target }}</p>'),
            HTML('<div class=well>'),
            'answer',
            HTML('</div>'),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Absenden</button> "
                 "<input action=\"action\" type=\"button\" value=\"Zurück\" class=\"btn btn-default\" "
                 "style=\"margin: 0.5em\" onclick=\"window.history.go(-1); return false;\" />"),
        )

        if self.object:
            if self.object.status == 1:
                self.helper.layout.\
                    fields.insert(2, HTML("<p><b>Ausgewählte Antwort: </b><br>Der Putzer gesteht den Fehler ein und "
                                          "hat die Aufgabe nun richtig gemacht. </p>"))
            else:
                self.helper.layout.\
                    fields.insert(2, HTML("<p><b>Ausgewählte Antwort: </b><br>Der Putzer bestreitet die "
                                          "Anschuldigung und meint, er habe die Aufgabe "
                                          "richtig gemacht. </p>"))


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ('task', 'creator_comments')

    task = \
        forms.ModelChoiceField(Task.objects.all(), label="Welche Aufgabe wurde nicht korrekt gemacht?", empty_label=None,
                               help_text="Wenn mehrere Aufgaben nicht korrekt gemacht wurden, muss zu jeder "
                                         "Aufgabe eine seperate Beschwerde eingereicht werden. Dadurch kann der "
                                         "beschuldigte Putzer zielgerichteter reagieren. Für Aufgaben, die noch "
                                         "nicht geputzt sind, können keine Beschwerden eingereicht werden.")
    creator_comments = forms.CharField(widget=forms.TextInput, max_length=50, label="Was hast du zu sagen?",
                                       help_text="Max. 50 Zeichen")

    def __init__(self, *args, **kwargs):
        if 'schedule' in kwargs:
            print(kwargs['schedule'].pk)
            self.__tasks = kwargs['schedule'].cleaningday_set.filter(
                    date__lte=timezone.now().date() + datetime.timedelta(days=7)).first().\
                tasks.filter(cleaned_by__isnull=False)
                    # date__lte=timezone.now().date()-app_config().timedelta_complaints_until_after_due()).first().tasks.all()
            kwargs.pop('schedule')
        else:
            self.__tasks = None
        super(ComplaintForm, self).__init__(*args, **kwargs)
        print("hi")
        print(self.__tasks)
        self.fields['task'].queryset = self.__tasks
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'task',
            'creator_comments',
            HTML("<button class=\"btn btn-danger\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Beschwerde abschicken</button> "
                 "<input action=\"action\" type=\"button\" value=\"Zurück\" class=\"btn btn-default\""
                 "onclick=\"window.history.go(-1); return false;\" />"),
        )


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Config
        fields = ('date_due', 'trust_in_users')

    date_due = forms.ChoiceField(choices=Config.WEEKDAYS, initial=6,
                                 label="Wochentag, für den Putzdienste definiert sind.",
                                 help_text="Dies ist nicht der Wochetag, bis den die Putzdienste gemacht sein müssen!")
    trust_in_users = forms.BooleanField(required=False, label="Putzer können sich ohne Passwort einloggen.",
                                        help_text="Eine Änderung dieses Feldes hat weitreichende Konsequenzen.")

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'date_due',
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

        start_date = timezone.now().date()
        end_date = start_date + datetime.timedelta(days=3*30)
        initial['start_date'] = str(start_date.day)+"."+str(start_date.month)+"."+str(start_date.year)
        initial['end_date'] = str(end_date.day)+"."+str(end_date.month)+"."+str(end_date.year)

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
        if slack_running():
            exclude = ('slug', 'user', 'time_zone')
        else:
            exclude = ('slack_id', 'slug', 'user', 'time_zone')

    name = forms.CharField(max_length=10, label="Name des Putzers",
                           required=True, widget=forms.TextInput)

    moved_in = forms.DateField(input_formats=['%d.%m.%Y'], label="Eingezogen am TT.MM.YYYY",
                               widget=forms.DateInput(format='%d.%m.%Y'))
    moved_out = forms.DateField(input_formats=['%d.%m.%Y'], label="Ausgezogen am TT.MM.YYYY",
                                widget=forms.DateInput(format='%d.%m.%Y'),
                                help_text="Falls du einen neuen Putzer erstellst, ist es eine gute Idee, diesen "
                                          "Wert auf das Einzugsdatum plus 3 Jahre zu setzen.")

    schedule_group = forms.\
        ModelChoiceField(queryset=ScheduleGroup.objects.all(),
                         required=True, empty_label=None,
                         widget=forms.RadioSelect,
                         label="Zugehörigkeit",
                         help_text="Wähle die Etage oder die Gruppe, zu der der Putzer gehört.")

    slack_id = forms.ChoiceField(choices=get_slack_users(), label="Wähle des Putzers Slackprofil aus.",
                                 required=False)

    def __init__(self, *args, **kwargs):
        # initial = kwargs.get('initial', {})
        # if 'instance' in kwargs and kwargs['instance']:
        #     initial['schedule_group'] = ScheduleGroup.objects.filter(cleaners=kwargs['instance'])
        #     if initial['schedule_group'].exists():
        #         initial['schedule_group'] = initial['schedule_group'].first().pk
        #     kwargs['initial'] = initial

        super(CleanerForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'moved_in',
            'moved_out',
            'schedule_group',
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Speichern</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Abbrechen</a> "),
        )

        if slack_running():
            self.helper.layout.fields.insert(4, 'slack_id')
        else:
            self.helper.layout.fields.insert(4, HTML("<p><i>Slack ist ausgeschaltet. Schalte Slack ein, um "
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
            if not kwargs['instance'].cleaner_set.all():
                self.helper.layout.fields.append(HTML(
                    "<a class=\"btn btn-danger pull-right\" style=\"color:whitesmoke;\""
                    "href=\"{% url 'webinterface:cleaning-schedule-group-delete' object.pk %}\""
                    "role=\"button\"><span class=\"glyphicon glyphicon-trash\"></span> "
                    "Lösche Putzplan-Gruppierung</a>"))
            else:
                self.helper.layout.fields.append(HTML(
                    "<p><i>Um diese Gruppe zu löschen müssen erst alle Putzer daraus entfernt werden. <br>"
                    "Diese sind: {% for cleaner in object.cleaners.all %} {{cleaner.name}} {% endfor %}</i></p>"))





