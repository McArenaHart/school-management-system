from django import forms
from django.utils import timezone
from .models import PaymentProof

class UploadPOPForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ["file", "note"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "note": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional note"}),
        }

class CreateInvoiceForm(forms.Form):
    student_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"class": "form-control"}))
    fee_structure_id = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control"}))
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    total_amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    parent_username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional: link invoice to parent username"})
    )
