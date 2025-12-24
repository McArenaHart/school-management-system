from django import forms
from .models import ClassGroup, Subject

class AttendancePickForm(forms.Form):
    class_group = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

class AssessmentFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search title/subject/class…"})
    )

class CreateAssessmentForm(forms.Form):
    class_group = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all().order_by("code"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    title = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    type = forms.ChoiceField(
        choices=[("test","test"),("exam","exam"),("assignment","assignment"),("project","project")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date","class":"form-control"}))
    max_score = forms.DecimalField(max_digits=7, decimal_places=2, initial=100, widget=forms.NumberInput(attrs={"class":"form-control"}))
    weight = forms.DecimalField(max_digits=7, decimal_places=2, initial=100, widget=forms.NumberInput(attrs={"class":"form-control"}))
