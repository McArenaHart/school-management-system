from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class AdmissionApplication(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("reviewed", "Reviewed"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    # Applicant details
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    date_of_birth = models.DateField()

    requested_grade = models.CharField(max_length=40, blank=True)

    # Guardian contact
    guardian_name = models.CharField(max_length=120)
    guardian_phone = models.CharField(max_length=40, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian_relationship = models.CharField(max_length=40, blank=True)

    notes = models.TextField(blank=True)

    # Filled when admitted (MVP linking)
    admitted_student_id = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.status})"
