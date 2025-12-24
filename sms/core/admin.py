from django.contrib import admin
from .models import AcademicYear, Term, SchoolSettings

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_editable = ("is_current",)
    ordering = ("-start_date",)

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "start_date", "end_date")
    list_filter = ("academic_year",)

@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ("school_name", "current_academic_year")
