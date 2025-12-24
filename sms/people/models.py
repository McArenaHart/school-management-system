from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="parent_profile")
    phone = models.CharField(max_length=30, blank=True)
    preferred_language = models.CharField(
        max_length=5,
        choices=[("en", "English"), ("sn", "Shona"), ("nd", "Ndebele")],
        default="en",
    )

    def __str__(self):
        return f"ParentProfile({self.user})"

class Student(models.Model):
    # Parents input basic student info (document) :contentReference[oaicite:3]{index=3}
    student_id = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    date_of_birth = models.DateField()
    admission_date = models.DateField()
    grade = models.CharField(max_length=20, blank=True)

    STATUS_CHOICES = [
        ("active", "Active"),
        ("graduated", "Graduated"),
        ("left", "Left"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    parent_users = models.ManyToManyField(User, blank=True, related_name="linked_students")

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    staff_code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
