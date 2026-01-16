from django.contrib.auth import authenticate, login, logout
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from people.models import Student, TeacherProfile
from academics.models import AttendanceRecord, ClassGroup, Subject
from finance.models import FeeInvoice
from comms.models import Thread, Message, NotificationLog
from registrar.models import AdmissionApplication
from .models import User


def _role_matches_user(user, selected_role: str) -> bool:
    """
    Enforce role-based interface selection at login (spec requirement).
    Superusers can enter any role, but we still default them to admin dashboard.
    """
    if user.is_superuser:
        return True

    selected_role = (selected_role or "").strip().lower()

    if selected_role == "principal":
        return user.is_principal
    if selected_role == "admin":
        return user.is_school_admin or user.is_staff
    if selected_role == "teacher":
        return user.is_teacher
    if selected_role == "parent":
        return user.is_parent

    return False


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        selected_role = request.POST.get("role", "").strip().lower()

        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Invalid username or password."
        else:
            if not selected_role:
                error = "Please select your role."
            elif not _role_matches_user(user, selected_role):
                error = "You selected a role that does not match your account."
            else:
                login(request, user)

                # Terms gate: must accept before using the system (spec requirement)
                if not user.has_accepted_terms():
                    return redirect("accounts:terms")

                return redirect("accounts:dashboard")

    return render(request, "accounts/login.html", {"error": error})


@login_required
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    # If terms not accepted, enforce immediately
    if not request.user.has_accepted_terms():
        return redirect("accounts:terms")

    role = request.user.primary_role()
    ctx = {"role": role, "notifications": NotificationLog.objects.none()}

    if role in ("principal", "admin"):
        employee_filter = (
            Q(is_principal=True)
            | Q(is_school_admin=True)
            | Q(is_teacher=True)
            | Q(is_staff=True)
        )
        employees_count = User.objects.filter(employee_filter).distinct().count()
        subjects_count = Subject.objects.count()
        since = timezone.localdate() - timedelta(days=30)
        attendance_rows = (
            AttendanceRecord.objects.filter(date__gte=since)
            .values("status")
            .annotate(total=Count("id"))
        )
        attendance_summary = {row["status"]: row["total"] for row in attendance_rows}
        absent_recent = (
            AttendanceRecord.objects.filter(status="absent", date__gte=since)
            .select_related("student", "class_group")
            .order_by("-date")[:5]
        )
        ctx.update(
            {
                "students_count": Student.objects.count(),
                "teachers_count": TeacherProfile.objects.count(),
                "employees_count": employees_count,
                "subjects_count": subjects_count,
                "unpaid_invoices": FeeInvoice.objects.filter(
                    status__in=["unpaid", "partial", "pending_verification"]
                ).count(),
                "finance_invoices_total": FeeInvoice.objects.count(),
                "finance_pending_verification": FeeInvoice.objects.filter(status="pending_verification").count(),
                "finance_overdue": FeeInvoice.objects.filter(
                    status__in=["unpaid", "partial"], due_date__lt=timezone.localdate()
                ).count(),
                "threads_count": Thread.objects.count(),
                "notifications": NotificationLog.objects.order_by("-created_at")[:10],
                "admissions_total": AdmissionApplication.objects.count(),
                "admissions_new": AdmissionApplication.objects.filter(status="new").count(),
                "admissions_accepted": AdmissionApplication.objects.filter(status="accepted").count(),
                "attendance_summary": attendance_summary,
                "absent_recent": absent_recent,
            }
        )

    elif role == "teacher":
        ctx.update(
            {
                "my_threads": Thread.objects.filter(teacher_user=request.user).count(),
                "my_sent_messages": Message.objects.filter(sender=request.user).count(),
                "class_groups_count": ClassGroup.objects.filter(homeroom_teacher=request.user).count(),
            }
        )

    elif role == "parent":
        ctx.update(
            {
                "linked_students": request.user.linked_students.all(),
                "my_invoices": FeeInvoice.objects.filter(parent_user=request.user).count(),
                "my_threads": Thread.objects.filter(parent_user=request.user).count(),
            }
        )

    return render(request, "accounts/dashboard.html", ctx)


@login_required
@require_http_methods(["GET", "POST"])
def terms_view(request):
    """
    Minimal Terms & Conditions acceptance flow.
    You can later move the actual terms text into a CMS/DB setting.
    """
    if request.method == "POST":
        request.user.accept_terms()
        return redirect("accounts:dashboard")

    return render(request, "accounts/terms.html")
