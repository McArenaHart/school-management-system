from django import forms
from .models import ParentProfile

class LinkStudentForm(forms.Form):
    student_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=60, widget=forms.TextInput(attrs={"class": "form-control"}))
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ["phone", "preferred_language"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+263..."}),
            "preferred_language": forms.Select(attrs={"class": "form-select"}),
        }

class NotificationPrefForm(forms.Form):
    enable_email = forms.BooleanField(required=False)
    enable_sms = forms.BooleanField(required=False)
    enable_in_app = forms.BooleanField(required=False)
