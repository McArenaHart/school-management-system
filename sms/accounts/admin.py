from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("SMS Roles", {"fields": ("is_principal", "is_school_admin", "is_teacher", "is_parent")}),
    )
    list_display = ("username", "email", "is_principal", "is_school_admin", "is_teacher", "is_parent", "is_staff")
    list_filter = ("is_principal", "is_school_admin", "is_teacher", "is_parent", "is_staff", "is_superuser")
