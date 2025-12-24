from django.db import models

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)  # "2025"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name

class Term(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=20)  # "Term 1"
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = ("academic_year", "name")
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name} {self.academic_year}"

class SchoolSettings(models.Model):
    school_name = models.CharField(max_length=255, default="BusyBee School")
    current_academic_year = models.OneToOneField(
        AcademicYear, on_delete=models.SET_NULL, null=True, blank=True, related_name="settings_current_for"
    )

    default_country = models.CharField(max_length=100, blank=True)
    default_timezone = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = "School settings"

    def __str__(self) -> str:
        return self.school_name
