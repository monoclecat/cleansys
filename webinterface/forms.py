from django import forms
from .models import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import FormActions


class ConfigForm(forms.Form):
    start_date = forms.DateField(input_formats=['%d.%m.%Y'], label="Start date DD.MM.YYYY")
    end_date = forms.DateField(input_formats=['%d.%m.%Y'], label="End date DD.MM.YYYY")

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Fieldset("General",
                     'start_date',
                     'end_date',
                     ),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Next</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:cleaners\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Cancel</a>"),
        )


class CleanerForm(forms.ModelForm):
    class Meta:
        model = Cleaner
        fields = '__all__'

    name = forms.CharField(max_length=10, label="Cleaner name", help_text="Please only the first name",
                           required=True, widget=forms.TextInput)

    assigned_to = forms.ModelMultipleChoiceField(queryset=CleaningSchedule.objects.all(), widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(CleanerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Fieldset("General",
                     'name',
                     'assigned_to',
                     ),
            HTML("<button class=\"btn btn-success\" type=\"submit\" name=\"save\">"
                 "<span class=\"glyphicon glyphicon-ok\"></span> Save</button> "
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:cleaners\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Cancel</a>"),
        )


class CleaningScheduleForm(forms.ModelForm):
    class Meta:
        model = CleaningSchedule
        fields = '__all__'

    name = forms.CharField(max_length=20, label="Cleaning plan name", help_text="The title of the cleaning plan",
                           required=True, widget=forms.TextInput)

    cleaners_per_date = forms.ChoiceField(choices=CleaningSchedule.CLEANERS_PER_DATE_CHOICES,
                                          label="Number of cleaners per cleaning date",
                                          help_text="Bathroom only needs 1 but kitchen needs 2.",
                                          required=True, initial=1)

    frequency = forms.ChoiceField(choices=CleaningSchedule.FREQUENCY_CHOICES, required=True, initial=1)

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
                     'frequency'
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
                 "<a class=\"btn btn-warning\" href=\"{% url \'webinterface:cleaning-schedule\' %}\" role=\"button\">"
                 "<span class=\"glyphicon glyphicon-remove\"></span> Cancel</a>"),
        )


