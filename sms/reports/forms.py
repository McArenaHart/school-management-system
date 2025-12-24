from django import forms
from django.utils import timezone
from people.models import Student

class ReportFilterForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all().order_by("last_name", "first_name"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get("start_date")
        ed = cleaned.get("end_date")
        if sd and ed and sd > ed:
            self.add_error("end_date", "End date must be after start date.")
        return cleaned

def default_range():
    today = timezone.localdate()
    return today.replace(day=1), today
