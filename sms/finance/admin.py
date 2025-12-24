from django.contrib import admin
from django.utils import timezone
from .models import FeeStructure, FeeInvoice, Payment, PaymentProof

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

class ProofInline(admin.TabularInline):
    model = PaymentProof
    extra = 0

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "amount")
    list_filter = ("grade",)

@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "parent_user", "total_amount", "status", "due_date")
    list_filter = ("status", "due_date")
    search_fields = ("student__student_id", "student__first_name", "student__last_name", "parent_user__username")
    inlines = [PaymentInline, ProofInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_date", "method", "reference")
    list_filter = ("method",)

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ("invoice", "uploaded_by", "uploaded_at", "verified", "verified_at")
    list_filter = ("verified",)

    actions = ["mark_verified"]

    def mark_verified(self, request, queryset):
        now = timezone.now()
        for proof in queryset:
            proof.verified = True
            proof.verified_at = now
            proof.save(update_fields=["verified", "verified_at"])
            inv = proof.invoice
            inv.status = "paid"
            inv.save(update_fields=["status"])
    mark_verified.short_description = "Mark selected proofs verified (and invoice paid)"
