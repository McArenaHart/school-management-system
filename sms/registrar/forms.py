from django import forms
from .models import AdmissionApplication
from academics.models import ClassGroup

class AdmissionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = [
            "first_name","last_name","date_of_birth","requested_grade",
            "guardian_name","guardian_phone","guardian_email","guardian_relationship",
            "notes",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class":"form-control"}),
            "last_name": forms.TextInput(attrs={"class":"form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type":"date","class":"form-control"}),
            "requested_grade": forms.TextInput(attrs={"class":"form-control"}),
            "guardian_name": forms.TextInput(attrs={"class":"form-control"}),
            "guardian_phone": forms.TextInput(attrs={"class":"form-control"}),
            "guardian_email": forms.EmailInput(attrs={"class":"form-control"}),
            "guardian_relationship": forms.TextInput(attrs={"class":"form-control"}),
            "notes": forms.Textarea(attrs={"class":"form-control","rows":3}),
        }

class AdmitForm(forms.Form):
    student_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class":"form-control"}))
    class_group = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class":"form-select"})
    )
    parent_username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Optional: link a parent username"})
    )
