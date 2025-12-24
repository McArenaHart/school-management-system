from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from finance.models import FeeInvoice, Payment
from people.models import Student
from academics.models import AttendanceRecord, Grade
from finance.models import FeeInvoice, Payment
from .forms import ReportFilterForm, default_range
from django.db import models

def _has_field(Model, name: str) -> bool:
    try:
        Model._meta.get_field(name)
        return True
    except Exception:
        return False

def _sum_field(qs, field_candidates):
    for f in field_candidates:
        if qs.model and _has_field(qs.model, f):
            return qs.aggregate(s=models.Sum(f))["s"] or 0
    return 0

def _order_by_first_existing(qs, candidates, default="-id"):
    for f in candidates:
        # allow "-field"
        raw = f[1:] if f.startswith("-") else f
        if _has_field(qs.model, raw):
            return qs.order_by(f)
    return qs.order_by(default)


def _is_staffish(u):
    return u.is_authenticated and (u.is_principal or u.is_school_admin or u.is_teacher)


def _student_allowed(user, student: Student) -> bool:
    if _is_staffish(user):
        return True
    if user.is_parent and user in student.parent_users.all():
        return True
    return False


def _build_report(student: Student, start_date, end_date):
    # Attendance
    attendance_qs = AttendanceRecord.objects.filter(
        student=student, date__gte=start_date, date__lte=end_date
    ).order_by("-date")

    present = attendance_qs.filter(status="present").count()
    late = attendance_qs.filter(status="late").count()
    absent = attendance_qs.filter(status="absent").count()
    total_att = attendance_qs.count()

    # Grades
    grades_qs = Grade.objects.filter(
        student=student,
        assessment__date__gte=start_date,
        assessment__date__lte=end_date,
    ).select_related("assessment", "assessment__subject").order_by("-assessment__date")

    # Fees
    invoices_qs = FeeInvoice.objects.filter(student=student)
    invoices_qs = _order_by_first_existing(invoices_qs, ["-issue_date", "-created_at", "-id"])

    payments_qs = Payment.objects.filter(invoice__student=student)
    payments_qs = _order_by_first_existing(payments_qs, ["-payment_date", "-paymentDate", "-created_at", "-id"])

    total_invoiced = _sum_field(invoices_qs, ["total_amount", "amount", "totalAmount"])
    total_paid = _sum_field(payments_qs, ["amount", "paid_amount", "paidAmount"])

    balance = max(total_invoiced - total_paid, 0)

    return {
        "student": student,
        "start_date": start_date,
        "end_date": end_date,
        "attendance": {
            "qs": attendance_qs[:200],
            "present": present,
            "late": late,
            "absent": absent,
            "total": total_att,
        },
        "grades": grades_qs[:200],
        "fees": {
            "invoices": invoices_qs[:50],
            "payments": payments_qs[:50],
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "balance": balance,
        },
    }


@login_required
def report_home(request):
    """
    Parents go straight to their first linked student's report generator.
    Staff get a generator with student picker.
    """
    sd, ed = default_range()

    if request.user.is_parent:
        student = request.user.linked_students.first()
        if not student:
            messages.info(request, "No linked student yet. Link a student first.")
            return redirect("people:link_student")
        return redirect(f"/reports/generate/?student={student.id}&start_date={sd}&end_date={ed}")

    # staff view
    form = ReportFilterForm(initial={"start_date": sd, "end_date": ed})
    return render(request, "reports/home.html", {"form": form})


@login_required
def generate_report(request):
    sd_default, ed_default = default_range()
    form = ReportFilterForm(request.GET or None)

    student = None
    start_date = sd_default
    end_date = ed_default

    if form.is_valid():
        student = form.cleaned_data.get("student")
        start_date = form.cleaned_data.get("start_date") or sd_default
        end_date = form.cleaned_data.get("end_date") or ed_default
    else:
        # even if invalid, still render the form
        student = None

    # Parent: force student to linked one (no picker)
    if request.user.is_parent:
        student = request.user.linked_students.first()
        if not student:
            messages.info(request, "No linked student yet. Link a student first.")
            return redirect("people:link_student")

    if not student:
        messages.info(request, "Select a student to generate a report.")
        return render(request, "reports/home.html", {"form": form})

    if not _student_allowed(request.user, student):
        messages.error(request, "Not allowed.")
        return redirect("reports:home")

    ctx = _build_report(student, start_date, end_date)
    ctx["form"] = form
    return render(request, "reports/report.html", ctx)


@login_required
def report_pdf(request, student_id: int):
    """
    Optional PDF export (simple, clean, printable).
    """
    student = get_object_or_404(Student, id=student_id)
    if not _student_allowed(request.user, student):
        return HttpResponse("Not allowed", status=403)

    # date range from querystring
    sd_default, ed_default = default_range()
    start_date = request.GET.get("start_date") or str(sd_default)
    end_date = request.GET.get("end_date") or str(ed_default)

    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date).date()
    except Exception:
        start_date, end_date = sd_default, ed_default

    ctx = _build_report(student, start_date, end_date)

    # ---- ReportLab PDF ----
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Student Report")
    y -= 22

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Student: {student.first_name} {student.last_name} ({student.student_id})")
    y -= 14
    if ctx["enrollment"]:
        c.drawString(50, y, f"Class: {ctx['enrollment'].class_group}")
        y -= 14
    c.drawString(50, y, f"Range: {start_date} to {end_date}")
    y -= 22

    att = ctx["attendance"]
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Attendance Summary")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Present: {att['present']}  Late: {att['late']}  Absent: {att['absent']}  Total: {att['total']}")
    y -= 20

    fees = ctx["fees"]
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Fees Summary")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Invoiced: {fees['total_invoiced']}  Paid: {fees['total_paid']}  Balance: {fees['balance']}")
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Recent Grades")
    y -= 14
    c.setFont("Helvetica", 9)

    for g in ctx["grades"][:15]:
        line = f"{g.assessment.date} · {g.assessment.subject} · {g.assessment.title}: {g.score}"
        c.drawString(50, y, line[:110])
        y -= 12
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 9)

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename=f"report_{student.student_id}_{start_date}_{end_date}.pdf")


from registrar.models import AdmissionApplication

def _is_adminish(u):
    return u.is_authenticated and (u.is_principal or u.is_school_admin)

@login_required
def dashboard(request):
    if not _is_adminish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    today = timezone.localdate()
    last_30 = today - timezone.timedelta(days=30)

    # Students
    students_total = Student.objects.count()
    students_active = Student.objects.filter(status__iexact="active").count()

    # Admissions pipeline
    admissions_new = AdmissionApplication.objects.filter(status="new").count()
    admissions_reviewed = AdmissionApplication.objects.filter(status="reviewed").count()
    admissions_accepted = AdmissionApplication.objects.filter(status="accepted").count()

    # Attendance (last 30 days)
    att_qs = AttendanceRecord.objects.filter(date__gte=last_30, date__lte=today)
    att_total = att_qs.count()
    att_present = att_qs.filter(status="present").count()
    att_absent = att_qs.filter(status="absent").count()
    att_late = att_qs.filter(status="late").count()

    # Fees
    inv_total = FeeInvoice.objects.count()
    inv_paid = FeeInvoice.objects.filter(status="paid").count()
    inv_pending = FeeInvoice.objects.filter(status="pending_verification").count()
    invoiced_sum = FeeInvoice.objects.aggregate(s=models.Sum("total_amount"))["s"] or 0
    paid_sum = Payment.objects.aggregate(s=models.Sum("amount"))["s"] or 0
    balance = max(invoiced_sum - paid_sum, 0)

    # Recent activity tables
    recent_apps = AdmissionApplication.objects.all().order_by("-created_at")[:10]
    recent_invoices = FeeInvoice.objects.select_related("student").order_by("-issue_date")[:10]
    recent_absences = AttendanceRecord.objects.filter(status="absent").select_related("student").order_by("-date")[:10]

    return render(request, "reports/dashboard.html", {
        "today": today,
        "students_total": students_total,
        "students_active": students_active,
        "admissions_new": admissions_new,
        "admissions_reviewed": admissions_reviewed,
        "admissions_accepted": admissions_accepted,
        "att_total": att_total,
        "att_present": att_present,
        "att_absent": att_absent,
        "att_late": att_late,
        "inv_total": inv_total,
        "inv_paid": inv_paid,
        "inv_pending": inv_pending,
        "invoiced_sum": invoiced_sum,
        "paid_sum": paid_sum,
        "balance": balance,
        "recent_apps": recent_apps,
        "recent_invoices": recent_invoices,
        "recent_absences": recent_absences,
        "last_30": last_30,
    })
