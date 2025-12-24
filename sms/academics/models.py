from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models import AcademicYear
from people.models import Student

User = settings.AUTH_USER_MODEL

class ClassGroup(models.Model):
    name = models.CharField(max_length=30)          # "Form 2A"
    grade_level = models.CharField(max_length=20)   # "Form 2"
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("name", "academic_year")
        ordering = ("academic_year", "grade_level", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.academic_year})"

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ("code",)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.PROTECT)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("student", "academic_year")

    def __str__(self) -> str:
        return f"{self.student} -> {self.class_group}"

class TimetableEntry(models.Model):
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="timetable")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    teacher_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    day_of_week = models.IntegerField(
        choices=[(0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu"), (4, "Fri"), (5, "Sat"), (6, "Sun")]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ("day_of_week", "start_time")

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance")
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("student", "class_group", "date")
        ordering = ("-date",)

class Assessment(models.Model):
    TYPE_CHOICES = [
        ("test", "Test"),
        ("exam", "Exam"),
        ("assignment", "Assignment"),
        ("project", "Project"),
    ]
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="assessments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="assessments")
    teacher_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    title = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=100)
    weight = models.DecimalField(max_digits=7, decimal_places=2, default=100)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ("-date", "-id")

class Grade(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=7, decimal_places=2)
    comment = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("assessment", "student")
