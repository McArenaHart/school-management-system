from django.conf import settings
from django.db import models
from django.utils import timezone
from people.models import Student

User = settings.AUTH_USER_MODEL

class Thread(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="threads")
    teacher_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teacher_threads")
    parent_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parent_threads")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("student", "teacher_user", "parent_user")

    def __str__(self):
        return f"{self.student} ({self.teacher_user} ↔ {self.parent_user})"

class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

class PerformanceNote(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="performance_notes")
    teacher_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    term_month = models.DateField(help_text="Use first day of month for grouping.")
    summary = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-term_month", "-created_at"]

class BehaviourRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="behaviour_records")
    teacher_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    occurred_on = models.DateField(default=timezone.now)
    note = models.TextField()

    class Meta:
        ordering = ["-occurred_on", "-id"]

class NotificationLog(models.Model):
    CHANNEL_CHOICES = [
        ("sms", "SMS"),
        ("email", "Email"),
        ("in_app", "In-App"),
    ]
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    to = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=40, default="queued")  # queued/sent/failed
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.channel} -> {self.to} [{self.status}]"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notif_pref")
    enable_email = models.BooleanField(default=True)
    enable_sms = models.BooleanField(default=False)
    enable_in_app = models.BooleanField(default=True)

    def __str__(self):
        return f"NotifPref({self.user})"


class ThreadReadState(models.Model):
    """
    Tracks the last time a user viewed a thread so we can compute unread messages.
    """
    thread = models.ForeignKey("Thread", on_delete=models.CASCADE, related_name="read_states")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="thread_read_states")
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("thread", "user")

    def __str__(self):
        return f"{self.user} read {self.thread} at {self.last_read_at}"