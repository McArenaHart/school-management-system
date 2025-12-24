from django import forms
from django.contrib.auth import get_user_model
from .models import Role, Permission

User = get_user_model()

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name", "description", "permissions"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "permissions": forms.SelectMultiple(attrs={"class": "form-select", "size": "12"}),
        }

class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ["code", "name"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. finance.verify_pop"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Verify proof of payment"}),
        }

class AssignRoleForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all().order_by("username"), widget=forms.Select(attrs={"class":"form-select"}))
    role = forms.ModelChoiceField(queryset=Role.objects.all().order_by("name"), widget=forms.Select(attrs={"class":"form-select"}))
