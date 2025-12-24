from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from people.models import Student
from accounts.models import User
from .forms import UploadPOPForm, CreateInvoiceForm
from .models import FeeInvoice, Payment, PaymentProof, FeeStructure


def _is_staffish(u):
    return u.is_authenticated and (u.is_principal or u.is_school_admin)


@login_required
def my_fees(request):
    u = request.user

    if u.is_parent:
        invoices = FeeInvoice.objects.filter(parent_user=u).select_related("student").order_by("-issue_date")
        # also show invoices for linked students even if parent_user isn't set (nice MVP)
        linked_ids = list(u.linked_students.values_list("id", flat=True))
        if linked_ids:
            invoices = FeeInvoice.objects.filter(student_id__in=linked_ids).select_related("student").order_by("-issue_date")
    else:
        invoices = FeeInvoice.objects.all().select_related("student", "parent_user").order_by("-issue_date")

    total_due = invoices.exclude(status="paid").aggregate(s=Sum("total_amount"))["s"] or 0
    paid_count = invoices.filter(status="paid").count()
    pending_count = invoices.filter(status="pending_verification").count()

    return render(
        request,
        "finance/my_fees.html",
        {
            "invoices": invoices[:200],
            "total_due": total_due,
            "paid_count": paid_count,
            "pending_count": pending_count,
            "is_staffish": _is_staffish(u),
        },
    )


@login_required
def invoice_detail(request, invoice_id: int):
    invoice = get_object_or_404(
        FeeInvoice.objects.select_related("student", "parent_user", "fee_structure"),
        id=invoice_id
    )

    # parents can only view invoices for their linked students
    if request.user.is_parent:
        if request.user not in invoice.student.parent_users.all():
            messages.error(request, "Not allowed.")
            return redirect("finance:my_fees")

    proofs = invoice.proofs.order_by("-uploaded_at")
    payments = invoice.payments.order_by("-payment_date")

    paid_sum = payments.aggregate(s=Sum("amount"))["s"] or 0
    remaining = max(invoice.total_amount - paid_sum, 0)

    return render(
        request,
        "finance/invoice_detail.html",
        {
            "invoice": invoice,
            "proofs": proofs,
            "payments": payments,
            "paid_sum": paid_sum,
            "remaining": remaining,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def upload_pop(request, invoice_id: int):
    invoice = get_object_or_404(FeeInvoice.objects.select_related("student"), id=invoice_id)

    if request.user.is_parent and request.user not in invoice.student.parent_users.all():
        messages.error(request, "Not allowed.")
        return redirect("finance:my_fees")

    form = UploadPOPForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        proof: PaymentProof = form.save(commit=False)
        proof.invoice = invoice
        proof.uploaded_by = request.user
        proof.save()

        invoice.status = "pending_verification"
        invoice.save(update_fields=["status"])

        messages.success(request, "Proof of payment uploaded. Awaiting verification.")
        return redirect("finance:invoice_detail", invoice_id=invoice.id)

    return render(request, "finance/upload_pop.html", {"invoice": invoice, "form": form})


@login_required
def verification_queue(request):
    if not _is_staffish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("finance:my_fees")

    q = (request.GET.get("q") or "").strip()

    proofs = PaymentProof.objects.filter(verified=False).select_related("invoice", "invoice__student", "uploaded_by").order_by("-uploaded_at")
    if q:
        proofs = proofs.filter(
            invoice__student__student_id__icontains=q
        ) | proofs.filter(
            invoice__student__last_name__icontains=q
        )

    return render(request, "finance/verification_queue.html", {"proofs": proofs[:300], "q": q})


@login_required
@require_http_methods(["POST"])
def verify_proof(request, proof_id: int):
    if not _is_staffish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("finance:my_fees")

    proof = get_object_or_404(PaymentProof.objects.select_related("invoice"), id=proof_id)
    invoice = proof.invoice

    # Mark proof verified and invoice paid (MVP simplification)
    proof.verified = True
    proof.verified_at = timezone.now()
    proof.save(update_fields=["verified", "verified_at"])

    invoice.status = "paid"
    invoice.save(update_fields=["status"])

    messages.success(request, f"Approved POP and marked Invoice #{invoice.id} as PAID.")
    return redirect("finance:verification_queue")


@login_required
@require_http_methods(["GET", "POST"])
def create_invoice(request):
    if not _is_staffish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("finance:my_fees")

    form = CreateInvoiceForm(request.POST or None)

    # helper lists for the UI
    fee_structures = FeeStructure.objects.all().order_by("name")[:200]

    if request.method == "POST" and form.is_valid():
        sid = form.cleaned_data["student_id"].strip()
        fee_structure_id = form.cleaned_data["fee_structure_id"]
        due_date = form.cleaned_data["due_date"]
        total_amount = form.cleaned_data["total_amount"]
        parent_username = (form.cleaned_data.get("parent_username") or "").strip()

        student = get_object_or_404(Student, student_id__iexact=sid)
        fee_structure = get_object_or_404(FeeStructure, id=fee_structure_id)

        parent_user = None
        if parent_username:
            parent_user = get_object_or_404(User, username=parent_username)

        inv = FeeInvoice.objects.create(
            student=student,
            parent_user=parent_user,
            fee_structure=fee_structure,
            issue_date=timezone.now().date(),
            due_date=due_date,
            total_amount=total_amount,
            status="unpaid",
        )

        messages.success(request, f"Invoice #{inv.id} created.")
        return redirect("finance:invoice_detail", invoice_id=inv.id)

    return render(request, "finance/create_invoice.html", {"form": form, "fee_structures": fee_structures})
