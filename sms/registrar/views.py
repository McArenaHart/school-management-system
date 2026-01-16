from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import User
from people.models import Student
from academics.models import Enrollment, ClassGroup
from core.models import AcademicYear, SchoolSettings
from .forms import AdmissionApplicationForm, AdmitForm, BulkApplicationUploadForm, BulkAdmitUploadForm
from .models import AdmissionApplication
from rbac.utils import attach_user_to_role_group
from rbac.constants import ROLE_PARENT
import csv
from io import TextIOWrapper
from datetime import datetime
from django.db import transaction

def _is_registrarish(u):
    return u.is_authenticated and (getattr(u, "is_registrar", False) or u.is_school_admin or u.is_principal)


def _current_academic_year():
    settings_obj = SchoolSettings.objects.first()
    if settings_obj and settings_obj.current_academic_year:
        return settings_obj.current_academic_year
    return AcademicYear.objects.order_by("-start_date").first()


def _generate_student_id(year: int) -> str:
    """Generate a student ID like A0012025 (A + sequence + year)."""
    prefix = "A"
    year_suffix = str(year)
    seq = 1
    while True:
        candidate = f"{prefix}{seq:03d}{year_suffix}"
        if not Student.objects.filter(student_id=candidate).exists():
            return candidate
        seq += 1


def _build_admit_form(app, data=None):
    grade_filter = (app.requested_grade or "").strip()
    form = AdmitForm(data if data is not None else None, grade_filter=grade_filter or None)
    class_group_notice = None
    qs = form.fields["class_group"].queryset

    if grade_filter and not qs.exists():
        all_qs = ClassGroup.objects.all().order_by("name")
        if all_qs.exists():
            form.fields["class_group"].queryset = all_qs
            class_group_notice = (
                f'No class groups match requested grade "{grade_filter}". '
                "Showing all class groups. Update the requested grade or add a class group for it."
            )
        else:
            class_group_notice = "No class groups have been created yet. Create one in Academics > Class groups."
    elif not grade_filter and not qs.exists():
        class_group_notice = "No class groups have been created yet. Create one in Academics > Class groups."

    return form, class_group_notice

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

    ay_exists = AcademicYear.objects.exists()
    class_groups_exist = ClassGroup.objects.exists()

    return render(
        request,
        "registrar/admissions_list.html",
        {
            "apps": qs[:250],
            "q": q,
            "status": status,
            "ay_exists": ay_exists,
            "class_groups_exist": class_groups_exist,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def apply(request):
    # Staff-only: registrar/principal/admin submit on behalf of applicants
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = AdmissionApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        app = form.save()
        messages.success(request, "Application submitted.")
        return redirect("registrar:application_detail", app_id=app.id)
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "registrar/apply.html", {"form": form})

@login_required
def application_detail(request, app_id: int):
    app = get_object_or_404(AdmissionApplication, id=app_id)
    can_manage = _is_registrarish(request.user)
    admit_form = None
    class_group_notice = None
    if can_manage and not app.admitted_student_id:
        admit_form, class_group_notice = _build_admit_form(app)
    admitted_student = Student.objects.filter(student_id=app.admitted_student_id).first() if app.admitted_student_id else None
    return render(
        request,
        "registrar/application_detail.html",
        {
            "app": app,
            "can_manage": can_manage,
            "admit_form": admit_form,
            "class_group_notice": class_group_notice,
            "admitted_student": admitted_student,
        },
    )

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
    if app.admitted_student_id:
        student = Student.objects.filter(student_id=app.admitted_student_id).first()
        if student:
            messages.info(request, f"Application already admitted as {student.first_name} {student.last_name}.")
            return redirect("people:student_detail", student_id=student.pk)
        messages.warning(request, "Application marked as accepted already; contact admin if you need to re-admit.")
        return redirect("registrar:application_detail", app_id=app.id)
    form, _ = _build_admit_form(app, data=request.POST)

    if not form.is_valid():
        messages.error(request, "Fix the form errors.")
        return redirect("registrar:application_detail", app_id=app.id)

    student_id = (form.cleaned_data.get("student_id") or "").strip()
    class_group = form.cleaned_data["class_group"]
    parent_username = (form.cleaned_data.get("parent_username") or "").strip()
    create_parent_user = form.cleaned_data.get("create_parent_user")
    parent_email = (form.cleaned_data.get("parent_email") or "").strip()

    ay = _current_academic_year()
    if not ay:
        messages.error(request, "No academic year configured. Create one in settings first.")
        return redirect("registrar:application_detail", app_id=app.id)

    # Generate student ID if not provided
    if not student_id:
        student_id = _generate_student_id(year=ay.start_date.year if ay.start_date else timezone.localdate().year)

    with transaction.atomic():
        student, created = Student.objects.get_or_create(
            student_id=student_id,
            defaults={
                "first_name": app.first_name,
                "last_name": app.last_name,
                "grade": app.requested_grade or "",
                "student_number": student_id,
            },
        )
        if not student.student_number:
            student.student_number = student_id
            student.save(update_fields=["student_number"])

        Enrollment.objects.get_or_create(student=student, class_group=class_group, academic_year=ay)

    # optional parent link
    if parent_username:
        try:
            parent = User.objects.get(username=parent_username)
            student.parent_users.add(parent)
        except User.DoesNotExist:
            messages.warning(request, "Parent username not found; student admitted without parent link.")
    elif create_parent_user:
        # auto-provision parent user
        if not parent_email:
            parent_email = app.guardian_email or ""
        base_username = (parent_email.split("@")[0] if parent_email else f"parent{student.student_id}").lower() or f"parent{student.student_id}"
        username = base_username
        idx = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{idx}"
            idx += 1
        parent_user = User.objects.create_user(username=username, email=parent_email or "")
        parent_user.is_parent = True
        parent_user.set_password("ChangeMe123!")
        parent_user.save()
        attach_user_to_role_group(parent_user, ROLE_PARENT)
        student.parent_users.add(parent_user)
        messages.success(request, f"Parent account created: {username} (password: ChangeMe123!).")

    # capacity warning
    enrolled = Enrollment.objects.filter(class_group=class_group, academic_year=ay).count()
    if class_group.capacity and enrolled > class_group.capacity:
        messages.warning(request, f"Class {class_group} is over capacity ({enrolled}/{class_group.capacity}).")

    app.status = "accepted"
    app.admitted_student_id = student.student_id
    app.save(update_fields=["status", "admitted_student_id"])

    messages.success(request, f"Admitted {student.first_name} {student.last_name} and enrolled in {class_group}.")
    return redirect("people:student_detail", student_id=student.pk)


@login_required
@require_http_methods(["POST"])
def remove_admitted_student(request, app_id: int):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    if not request.user.is_principal and not request.user.is_superuser:
        messages.error(request, "Only the principal can remove admitted students.")
        return redirect("registrar:application_detail", app_id=app_id)

    app = get_object_or_404(AdmissionApplication, id=app_id)
    if not app.admitted_student_id:
        messages.error(request, "No student to remove.")
        return redirect("registrar:application_detail", app_id=app.id)

    ay = _current_academic_year()
    student = Student.objects.filter(student_id=app.admitted_student_id).first()
    with transaction.atomic():
        if student:
            Enrollment.objects.filter(student=student, academic_year=ay).delete()
            student.delete()
        app.admitted_student_id = None
        app.status = "new"
        app.save(update_fields=["status", "admitted_student_id"])

    messages.success(request, "Admitted student removed; application reset to new.")
    return redirect("registrar:application_detail", app_id=app.id)


@login_required
@require_http_methods(["GET", "POST"])
def bulk_applications_upload(request):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = BulkApplicationUploadForm(request.POST or None, request.FILES or None)
    summary = None
    errors = []

    if request.method == "POST" and form.is_valid():
        f = request.FILES.get("csv_file")
        created = 0
        skipped = 0
        try:
            reader = csv.DictReader(TextIOWrapper(f.file, encoding="utf-8-sig"))
            for idx, row in enumerate(reader, start=2):
                fn = (row.get("first_name") or "").strip()
                ln = (row.get("last_name") or "").strip()
                dob_raw = (row.get("date_of_birth") or "").strip()
                guardian_name = (row.get("guardian_name") or "").strip()
                if not (fn and ln and dob_raw and guardian_name):
                    skipped += 1
                    errors.append(f"Row {idx}: missing required fields (first/last/dob/guardian).")
                    continue
                try:
                    dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                except ValueError:
                    skipped += 1
                    errors.append(f"Row {idx}: invalid date_of_birth '{dob_raw}', expected YYYY-MM-DD.")
                    continue

                AdmissionApplication.objects.create(
                    first_name=fn,
                    last_name=ln,
                    date_of_birth=dob,
                    requested_grade=(row.get("requested_grade") or "").strip(),
                    guardian_name=guardian_name,
                    guardian_phone=(row.get("guardian_phone") or "").strip(),
                    guardian_email=(row.get("guardian_email") or "").strip(),
                    guardian_relationship=(row.get("guardian_relationship") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                    status="new",
                )
                created += 1
            summary = {"created": created, "skipped": skipped}
            messages.success(request, "Bulk applications imported.")
        except Exception as exc:
            messages.error(request, f"Import failed: {exc}")

    return render(request, "registrar/bulk_applications_upload.html", {"form": form, "summary": summary, "errors": errors})


@login_required
@require_http_methods(["GET", "POST"])
def bulk_admit_upload(request):
    if not _is_registrarish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = BulkAdmitUploadForm(request.POST or None, request.FILES or None)
    summary = None
    errors = []

    if request.method == "POST" and form.is_valid():
        f = request.FILES.get("csv_file")
        default_grade = (form.cleaned_data.get("default_grade") or "").strip()
        default_class_group = (form.cleaned_data.get("default_class_group") or "").strip()
        created_students = 0
        enrollments_created = 0
        parent_linked = 0
        skipped = 0

        ay = _current_academic_year()
        try:
            reader = csv.DictReader(TextIOWrapper(f.file, encoding="utf-8-sig"))
            for idx, row in enumerate(reader, start=2):
                sid = (row.get("student_id") or "").strip()
                fn = (row.get("first_name") or "").strip()
                ln = (row.get("last_name") or "").strip()
                dob_raw = (row.get("date_of_birth") or "").strip()
                grade = (row.get("grade") or default_grade).strip()
                class_name = (row.get("class_group") or default_class_group).strip()
                ay_name = (row.get("academic_year") or "").strip()
                parent_username = (row.get("parent_username") or "").strip()
                parent_email = (row.get("parent_email") or "").strip()

                if not (fn and ln and dob_raw):
                    skipped += 1
                    errors.append(f"Row {idx}: missing required fields (names, dob).")
                    continue
                if not class_name:
                    skipped += 1
                    errors.append(f"Row {idx}: missing class_group (and no default).")
                    continue
                try:
                    dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                except ValueError:
                    skipped += 1
                    errors.append(f"Row {idx}: invalid date_of_birth '{dob_raw}', expected YYYY-MM-DD.")
                    continue

                ay_obj = ay
                if ay_name:
                    ay_obj = AcademicYear.objects.filter(name=ay_name).first()
                    if not ay_obj:
                        errors.append(f"Row {idx}: academic_year '{ay_name}' not found; using current.")
                        ay_obj = ay

                if not ay_obj:
                    skipped += 1
                    errors.append(f"Row {idx}: no academic year available; create one first.")
                    continue

                cg, _ = ClassGroup.objects.get_or_create(
                    name=class_name,
                    academic_year=ay_obj,
                    defaults={"grade_level": grade or class_name},
                )

                # Generate student ID if not provided
                if not sid:
                    sid = _generate_student_id(year=ay_obj.start_date.year if ay_obj.start_date else timezone.localdate().year)

                student, was_created = Student.objects.get_or_create(
                    student_id=sid,
                    defaults={
                        "first_name": fn,
                        "last_name": ln,
                        "grade": grade,
                        "student_number": sid,
                    },
                )
                if was_created:
                    created_students += 1
                if not student.student_number:
                    student.student_number = sid
                    student.save(update_fields=["student_number"])
                enr, enr_created = Enrollment.objects.get_or_create(student=student, class_group=cg, academic_year=ay_obj)
                if enr_created:
                    enrollments_created += 1

                if parent_username:
                    try:
                        parent = User.objects.get(username=parent_username)
                        student.guardians.add(parent)
                        parent_linked += 1
                    except User.DoesNotExist:
                        errors.append(f"Row {idx}: parent username '{parent_username}' not found; skipped link.")
                elif parent_email:
                    base_username = parent_email.split("@")[0].lower() if "@" in parent_email else parent_email
                    if not base_username:
                        base_username = f"parent{sid}"
                    username = base_username
                    u_idx = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{u_idx}"
                        u_idx += 1
                    parent_user = User.objects.create_user(username=username, email=parent_email)
                    parent_user.is_parent = True
                    parent_user.set_password("ChangeMe123!")
                    parent_user.save()
                    attach_user_to_role_group(parent_user, ROLE_PARENT)
                    student.guardians.add(parent_user)
                    parent_linked += 1

                # capacity warning
                enrolled = Enrollment.objects.filter(class_group=cg, academic_year=ay_obj).count()
                if cg.capacity and enrolled > cg.capacity:
                    errors.append(f"Row {idx}: class {cg.name} over capacity ({enrolled}/{cg.capacity}).")

            summary = {
                "students_created": created_students,
                "enrollments_created": enrollments_created,
                "parents_linked": parent_linked,
                "skipped": skipped,
            }
            messages.success(request, "Bulk admit/import completed.")
        except Exception as exc:
            messages.error(request, f"Import failed: {exc}")

    return render(request, "registrar/bulk_admit_upload.html", {"form": form, "summary": summary, "errors": errors})
