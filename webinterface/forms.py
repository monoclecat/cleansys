from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import FormActions


class ConfigForm(forms.Form):
    start_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Start date DD.MM.YYYY")
    end_date = forms.DateField(input_formats=['%d.%m.%Y'], label="End date DD.MM.YYYY")

    show_deviations = forms.BooleanField(widget=forms.CheckboxInput, required=False,
                                         label="Show average absolute deviations (not really important)")

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML(
                "<a class=\"btn btn-default\" href=\"{% url 'webinterface:welcome' %}\" role=\"button\" style=\"margin:0.5em 1em 0.5em 0.5em\">"
                "<span class=\"glyphicon glyphicon-chevron-left\"></span> Back</a>"
            ),
            'start_date',
            'end_date',
            HTML(
                "<button class=\"btn btn-success\" type=\"submit\" name=\"save\" style=\"margin:0.5em 0.5em 0.5em 1em\">"
                "<span class=\"glyphicon glyphicon-chevron-right\"></span> Next</button> "),
            HTML("<br>"),
            Field('show_deviations')
        )


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        fields = '__all__'

    name = forms.CharField(max_length=10, label="Cleaner name",
                           required=True, widget=forms.TextInput)

    moved_in = forms.DateField(input_formats=['%d.%m.%Y'], label="Moved in on DD.MM.YYYY",
                               widget=forms.DateInput(format='%d.%m.%Y'))
    moved_out = forms.DateField(input_formats=['%d.%m.%Y'], label="Moves out on DD.MM.YYYY",
                                widget=forms.DateInput(format='%d.%m.%Y'),
                                help_text="When creating a new cleaner, set this to moved-in date plus "
                                          "3 years for good measure.")

    def __init__(self, *args, **kwargs):
        super(CleanerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Fieldset("General",
                     'name',
                     'moved_in',
                     'moved_out'
                     ),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Save</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Cancel</a>"),
        )


class CleaningScheduleForm(forms.ModelForm):
    class Meta:
        model = CleaningSchedule
        exclude = ('duties', )

    name = forms.CharField(max_length=20, label="Cleaning plan name", help_text="The title of the cleaning plan",
                           required=True, widget=forms.TextInput)

    cleaners_per_date = forms.ChoiceField(choices=CleaningSchedule.CLEANERS_PER_DATE_CHOICES,
                                          label="Number of cleaners per cleaning date",
                                          help_text="Bathroom only needs 1 but kitchen needs 2.",
                                          required=True, initial=1)

    frequency = forms.ChoiceField(choices=CleaningSchedule.FREQUENCY_CHOICES, required=True, initial=1,
                                  label="Cleaning schedule frequency",
                                  help_text="If you have two cleaning schedules that are due every two weeks "
                                            "but can't be on the same dates, set one to 'Even weeks' and the other "
                                            "to 'Odd weeks'")

    cleaners = forms.ModelMultipleChoiceField(queryset=Cleaner.objects.all(), required=False,
                                              widget=forms.CheckboxSelectMultiple(), label="Cleaners",
                                              help_text="Select the people that are assigned to this schedule.")

    task1 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task2 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task3 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task4 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task5 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task6 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task7 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task8 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task9 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                            help_text=" ")
    task10 = forms.CharField(max_length=40, required=False, widget=forms.TextInput, label="",
                             help_text=" ")

    def __init__(self, *args, **kwargs):
        super(CleaningScheduleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Fieldset("General",
                     'name',
                     'cleaners_per_date',
                     'frequency',
                     'cleaners'
                     ),
            Fieldset("Tasks (from left to right)",
                     'task1',
                     'task2',
                     'task3',
                     'task4',
                     'task5',
                     'task6',
                     'task7',
                     'task8',
                     'task9',
                     'task10',
                     ),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Save</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:config\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Cancel</a>"),
        )


