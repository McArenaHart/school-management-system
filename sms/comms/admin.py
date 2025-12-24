from django.contrib import admin
from .models import Thread, Message, PerformanceNote, BehaviourRecord, NotificationLog, ThreadReadState, NotificationPreference

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("student", "teacher_user", "parent_user", "created_at")
    search_fields = ("student__student_id", "teacher_user__username", "parent_user__username")
    inlines = [MessageInline]

@admin.register(PerformanceNote)
class PerformanceNoteAdmin(admin.ModelAdmin):
    list_display = ("student", "teacher_user", "term_month", "created_at")
    list_filter = ("term_month",)
    search_fields = ("student__student_id", "student__first_name", "student__last_name")

@admin.register(BehaviourRecord)
class BehaviourRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "teacher_user", "occurred_on")
    list_filter = ("occurred_on",)
    search_fields = ("student__student_id", "student__first_name", "student__last_name")

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("channel", "to", "status", "created_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("to", "subject", "body")

@admin.register(ThreadReadState)
class ThreadReadStateAdmin(admin.ModelAdmin):
    list_display = ("thread", "user", "last_read_at")
    search_fields = ("user__username",)
    list_filter = ("last_read_at",)

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "enable_email", "enable_sms", "enable_in_app")
    list_filter = ("enable_email", "enable_sms", "enable_in_app")
    search_fields = ("user__username", "user__email")
