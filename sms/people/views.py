from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from rbac.utils import require_any_perm

from .forms import ClassRoomForm, LinkStudentForm, StudentForm
from .models import ClassRoom, Student
from academics.models import AttendanceRecord, Enrollment
from core.models import AcademicYear, SchoolSettings
from finance.models import FeeInvoice


def _is_parent(user) -> bool:
    return getattr(user, "is_parent", False) or user.groups.filter(name="Parent").exists()


def _is_teacher(user) -> bool:
    return getattr(user, "is_teacher", False) or user.groups.filter(name="Teacher").exists()


def _current_academic_year():
    settings_obj = SchoolSettings.objects.first()
    if settings_obj and settings_obj.current_academic_year:
        return settings_obj.current_academic_year
    return AcademicYear.objects.order_by("-start_date").first()


@require_any_perm("people.view_student", "people.change_student", "people.add_student")
def students_list(request):
    q = request.GET.get("q", "").strip()

    qs = Student.objects.all()

    # If teacher: restrict to "their students" later (once you have class assignments)
    # For now: allow teacher to view students if they have people.view_student.
    # If parent: must never reach this view.
    if _is_parent(request.user) and not request.user.is_superuser:
        raise PermissionDenied

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(student_number__icontains=q)
            | Q(grade__icontains=q)
            | Q(classroom__name__icontains=q)
        )

    return render(
        request,
        "people/students_list.html",
        {
            "students": qs[:300],
            "q": q,
            "can_delete_student": request.user.has_perm("people.delete_student"),
        },
    )


@require_any_perm("people.view_student", "people.change_student", "people.add_student")
def students_dashboard(request):
    q = (request.GET.get("q") or "").strip()

    if _is_parent(request.user) and not request.user.is_superuser:
        raise PermissionDenied

    qs = Student.objects.select_related("classroom").annotate(guardians_count=Count("guardians"))
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(student_id__icontains=q)
            | Q(student_number__icontains=q)
            | Q(grade__icontains=q)
            | Q(classroom__name__icontains=q)
        )

    students = list(qs.order_by("last_name", "first_name")[:300])
    student_ids = [s.id for s in students]

    enrollment_map = {}
    attendance_map = {}
    fee_map = {}

    current_ay = _current_academic_year()

    if student_ids:
        enrollments = Enrollment.objects.select_related("class_group", "academic_year")\
            .filter(student_id__in=student_ids)
        if current_ay:
            enrollments = enrollments.filter(academic_year=current_ay)
        else:
            enrollments = enrollments.order_by("student_id", "-academic_year__start_date")
        for enr in enrollments:
            if enr.student_id not in enrollment_map:
                enrollment_map[enr.student_id] = enr

        since = timezone.localdate() - timedelta(days=30)
        attendance_rows = AttendanceRecord.objects.filter(
            student_id__in=student_ids,
            date__gte=since,
        ).values("student_id").annotate(
            present=Count("id", filter=Q(status="present")),
            late=Count("id", filter=Q(status="late")),
            absent=Count("id", filter=Q(status="absent")),
            total=Count("id"),
            last_date=Max("date"),
        )
        attendance_map = {row["student_id"]: row for row in attendance_rows}

        invoices = FeeInvoice.objects.filter(student_id__in=student_ids).annotate(
            paid=Sum("payments__amount"),
        ).order_by("student_id", "-due_date", "-issue_date", "-id")
        for inv in invoices:
            if inv.student_id in fee_map:
                continue
            paid = inv.paid or Decimal("0.00")
            balance = inv.total_amount - paid
            fee_map[inv.student_id] = {
                "invoice_id": inv.id,
                "status": inv.status,
                "total": inv.total_amount,
                "paid": paid,
                "balance": balance,
                "due_date": inv.due_date,
            }

    rows = [
        {
            "student": s,
            "enrollment": enrollment_map.get(s.id),
            "attendance": attendance_map.get(s.id),
            "fee": fee_map.get(s.id),
        }
        for s in students
    ]

    return render(
        request,
        "people/students_dashboard.html",
        {"rows": rows, "q": q, "current_ay": current_ay},
    )


@require_any_perm("people.add_student")
@require_http_methods(["GET", "POST"])
def student_create(request):
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        s = form.save()
        messages.success(request, "Student created.")
        return redirect("people:student_detail", s.id)
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "people/student_form.html", {"form": form, "mode": "create"})


@require_any_perm("people.change_student")
@require_http_methods(["GET", "POST"])
def student_edit(request, student_id: int):
    student = get_object_or_404(Student, id=student_id)
    form = StudentForm(request.POST or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Student updated.")
        return redirect("people:student_detail", student.id)
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "people/student_form.html", {"form": form, "mode": "edit", "student": student})


@require_any_perm("people.view_student", "people.change_student")
def student_detail(request, student_id: int):
    student = get_object_or_404(Student, id=student_id)

    # Parent access: only if linked to the student
    if _is_parent(request.user) and not request.user.is_superuser:
        if not student.guardians.filter(id=request.user.id).exists():
            raise PermissionDenied

    return render(
        request,
        "people/student_detail.html",
        {"student": student, "can_delete_student": request.user.has_perm("people.delete_student")},
    )


@require_any_perm("people.delete_student")
@require_http_methods(["POST"])
def student_delete(request, student_id: int):
    student = get_object_or_404(Student, id=student_id)
    if _is_parent(request.user) and not request.user.is_superuser:
        raise PermissionDenied
    student.delete()
    messages.success(request, "Student record deleted.")
    return redirect("people:students_list")


@login_required
@require_http_methods(["GET", "POST"])
def my_children(request):
    # Parents only (principal/admin can still open it but it will show empty)
    if not request.user.is_superuser and not _is_parent(request.user):
        raise PermissionDenied

    students = request.user.linked_students.all()
    return render(request, "people/my_children.html", {"students": students})


@login_required
@require_http_methods(["GET", "POST"])
def link_student(request):
    """
    Parent links to student using entered details (spec requirement).
    For MVP we do a best-match and require admin approval later if needed.
    """
    if not request.user.is_superuser and not _is_parent(request.user):
        raise PermissionDenied

    form = LinkStudentForm(request.POST or None)
    match = None

    if request.method == "POST" and form.is_valid():
        first_name = form.cleaned_data["first_name"].strip()
        last_name = form.cleaned_data["last_name"].strip()
        grade = (form.cleaned_data.get("grade") or "").strip()
        student_number = (form.cleaned_data.get("student_number") or "").strip()

        qs = Student.objects.all()

        # Prefer student_number match if provided
        if student_number:
            qs = qs.filter(student_number__iexact=student_number)
        else:
            qs = qs.filter(first_name__iexact=first_name, last_name__iexact=last_name)
            if grade:
                qs = qs.filter(grade__iexact=grade)

        match = qs.first()
        if not match:
            messages.error(request, "No matching student found. Please confirm details with the school.")
        else:
            match.guardians.add(request.user)
            messages.success(request, f"Linked to {match}.")
            return redirect("people:my_children")
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")

    return render(request, "people/link_student.html", {"form": form, "match": match})


# Classrooms (admin/IT only)
@require_any_perm("people.add_classroom", "people.change_classroom", "people.view_classroom")
def classrooms_list(request):
    rooms = ClassRoom.objects.order_by("name")
    return render(request, "people/classrooms_list.html", {"rooms": rooms})


@require_any_perm("people.add_classroom")
@require_http_methods(["GET", "POST"])
def classroom_create(request):
    form = ClassRoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Class created.")
        return redirect("people:classrooms")
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "people/classroom_form.html", {"form": form, "mode": "create"})
