from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import User
from people.models import Student
from academics.models import Enrollment
from .forms import AdmissionApplicationForm, AdmitForm
from .models import AdmissionApplication

def _is_registrarish(u):
    return u.is_authenticated and (getattr(u, "is_registrar", False) or u.is_school_admin or u.is_principal)

@login_required
def admissions_list(request):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()

    qs = AdmissionApplication.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(guardian_name__icontains=q) |
            Q(guardian_email__icontains=q)
        )

    return render(request, "registrar/admissions_list.html", {"apps": qs[:250], "q": q, "status": status})

@login_required
@require_http_methods(["GET", "POST"])
def apply(request):
    # allow public? MVP: require login (admin/registrar can submit on behalf)
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    form = AdmissionApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        app = form.save()
        messages.success(request, "Application submitted.")
        return redirect("registrar:application_detail", app_id=app.id)
    return render(request, "registrar/apply.html", {"form": form})

@login_required
def application_detail(request, app_id: int):
    app = get_object_or_404(AdmissionApplication, id=app_id)
    can_manage = _is_registrarish(request.user)
    admit_form = AdmitForm() if can_manage else None
    return render(request, "registrar/application_detail.html", {"app": app, "can_manage": can_manage, "admit_form": admit_form})

@login_required
def mark_status(request, app_id: int, status: str):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    app = get_object_or_404(AdmissionApplication, id=app_id)
    allowed = {"new","reviewed","accepted","rejected"}
    if status not in allowed:
        messages.error(request, "Invalid status.")
        return redirect("registrar:application_detail", app_id=app.id)

    app.status = status
    app.save(update_fields=["status"])
    messages.success(request, f"Status updated to {status}.")
    return redirect("registrar:application_detail", app_id=app.id)

@login_required
@require_http_methods(["POST"])
def admit_application(request, app_id: int):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    app = get_object_or_404(AdmissionApplication, id=app_id)
    form = AdmitForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Fix the form errors.")
        return redirect("registrar:application_detail", app_id=app.id)

    student_id = form.cleaned_data["student_id"].strip()
    class_group = form.cleaned_data["class_group"]
    parent_username = (form.cleaned_data.get("parent_username") or "").strip()

    student, created = Student.objects.get_or_create(
        student_id=student_id,
        defaults={
            "first_name": app.first_name,
            "last_name": app.last_name,
            "date_of_birth": app.date_of_birth,
            "admission_date": timezone.localdate(),
            "status": "active",
            "grade": app.requested_grade or "",
        }
    )

    # enroll (academic year stored on Enrollment)
    Enrollment.objects.get_or_create(student=student, class_group=class_group, defaults={"academic_year": str(timezone.localdate().year)})

    # optional parent link
    if parent_username:
        try:
            parent = User.objects.get(username=parent_username)
            student.parent_users.add(parent)
        except User.DoesNotExist:
            messages.warning(request, "Parent username not found; student admitted without parent link.")

    app.status = "accepted"
    app.admitted_student_id = student.student_id
    app.save(update_fields=["status", "admitted_student_id"])

    messages.success(request, f"Admitted {student.first_name} {student.last_name} and enrolled in {class_group}.")
    return redirect("people:student_detail", student_pk=student.pk)
