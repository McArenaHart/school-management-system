from django import forms
from people.models import Student

class StartThreadForm(forms.Form):
    student_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class": "form-control"}))
    parent_username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))


class MessageForm(forms.Form):
    body = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Type your message…",
        })
    )
