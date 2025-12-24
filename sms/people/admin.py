from django.contrib import admin
from .models import Student, TeacherProfile, ParentProfile

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "first_name", "last_name", "grade", "status")
    search_fields = ("student_id", "first_name", "last_name")
    list_filter = ("status", "grade")
    filter_horizontal = ("parent_users",)

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("staff_code", "user")
    search_fields = ("staff_code", "user__username", "user__first_name", "user__last_name")

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "preferred_language")
    search_fields = ("user__username", "user__email", "phone")
    list_filter = ("preferred_language",)
