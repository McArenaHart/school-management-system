from django.contrib import admin
from .models import ClassGroup, Subject, Enrollment, TimetableEntry, AttendanceRecord, Assessment, Grade

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0

class TimetableInline(admin.TabularInline):
    model = TimetableEntry
    extra = 0

@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "grade_level", "academic_year")
    list_filter = ("academic_year", "grade_level")
    search_fields = ("name",)
    inlines = [EnrollmentInline, TimetableInline]

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "class_group", "academic_year")
    list_filter = ("academic_year", "class_group")
    search_fields = ("student__student_id", "student__first_name", "student__last_name")

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ("class_group", "subject", "teacher_user", "day_of_week", "start_time", "end_time", "room")
    list_filter = ("class_group", "day_of_week")
    search_fields = ("class_group__name", "subject__code", "subject__name", "teacher_user__username")

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "class_group", "student", "status", "recorded_by")
    list_filter = ("date", "class_group", "status")
    search_fields = ("student__student_id", "student__first_name", "student__last_name")

class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("date", "class_group", "subject", "title", "type", "max_score", "weight", "teacher_user")
    list_filter = ("class_group", "subject", "type", "date")
    search_fields = ("title", "subject__name", "subject__code")
    inlines = [GradeInline]

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("assessment", "student", "score")
    list_filter = ("assessment__class_group", "assessment__subject")
    search_fields = ("student__student_id", "student__first_name", "student__last_name", "assessment__title")
