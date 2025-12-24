from django.conf import settings
from django.db import models
from django.utils import timezone
from people.models import Student

User = settings.AUTH_USER_MODEL

class FeeStructure(models.Model):
    name = models.CharField(max_length=120)
    grade = models.CharField(max_length=20, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.grade})"

class FeeInvoice(models.Model):
    STATUS = [
        ("unpaid", "Unpaid"),
        ("partial", "Partially Paid"),
        ("paid", "Paid"),
        ("pending_verification", "Pending Verification"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="invoices")
    parent_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS, default="unpaid")

    def __str__(self):
        return f"Invoice #{self.id} - {self.student}"

class Payment(models.Model):
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name="payments")
    payment_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=30, default="bank/mobile")
    reference = models.CharField(max_length=120, blank=True)

class PaymentProof(models.Model):
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name="proofs")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    file = models.FileField(upload_to="payment_proofs/")
    note = models.CharField(max_length=255, blank=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
