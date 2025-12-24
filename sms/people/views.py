from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from comms.models import NotificationPreference
from .forms import LinkStudentForm, ParentProfileForm, NotificationPrefForm
from .models import ParentProfile, Student

def _is_staffish(user):
    return user.is_authenticated and (user.is_principal or user.is_school_admin)

@login_required
def my_students(request):
    """
    Parent: show linked students.
    Staff/Principal/Admin: show quick links + directory entry point.
    """
    if request.user.is_parent:
        students = request.user.linked_students.all().order_by("last_name", "first_name")
        return render(request, "people/my_students.html", {"students": students})

    # Staff/Principal/Admin landing
    return render(request, "people/people_home_staff.html")

@login_required
def link_student(request):
    if not request.user.is_parent:
        messages.info(request, "Only parent accounts can link students.")
        return redirect("people:my_students")

    form = LinkStudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sid = form.cleaned_data["student_id"].strip()
        ln = form.cleaned_data["last_name"].strip()
        dob = form.cleaned_data["date_of_birth"]

        try:
            student = Student.objects.get(
                student_id__iexact=sid,
                last_name__iexact=ln,
                date_of_birth=dob,
            )
        except Student.DoesNotExist:
            messages.error(request, "No matching student found. Check Student ID, surname, and date of birth.")
            return render(request, "people/link_student.html", {"form": form})

        student.parent_users.add(request.user)
        messages.success(request, f"Linked successfully: {student.first_name} {student.last_name}.")
        return redirect("people:my_students")

    return render(request, "people/link_student.html", {"form": form})

@login_required
def student_detail(request, student_pk: int):
    student = get_object_or_404(Student, pk=student_pk)

    # Access control:
    # - Parent can view only if linked
    # - Staff/principal/admin can view all
    if request.user.is_parent and request.user not in student.parent_users.all():
        messages.error(request, "You are not linked to that student.")
        return redirect("people:my_students")

    return render(request, "people/student_detail.html", {"student": student})

@login_required
def student_directory(request):
    if not _is_staffish(request.user):
        messages.error(request, "Not allowed.")
        return redirect("people:my_students")

    q = (request.GET.get("q") or "").strip()
    qs = Student.objects.all().order_by("last_name", "first_name")
    if q:
        qs = qs.filter(
            Q(student_id__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(grade__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "people/student_directory.html", {"page": page, "q": q})

@login_required
def settings_view(request):
    """
    Parent settings:
    - Parent profile (phone + preferred language)
    - Notification preferences (email/sms/in-app)
    """
    if not request.user.is_parent:
        messages.info(request, "Settings page is available for parent accounts in this MVP.")
        return redirect("people:my_students")

    profile, _ = ParentProfile.objects.get_or_create(user=request.user)
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)

    profile_form = ParentProfileForm(request.POST or None, instance=profile)
    pref_form = NotificationPrefForm(
        request.POST or None,
        initial={
            "enable_email": pref.enable_email,
            "enable_sms": pref.enable_sms,
            "enable_in_app": pref.enable_in_app,
        },
    )

    if request.method == "POST":
        ok = True
        if profile_form.is_valid():
            profile_form.save()
        else:
            ok = False

        if pref_form.is_valid():
            pref.enable_email = bool(pref_form.cleaned_data.get("enable_email"))
            pref.enable_sms = bool(pref_form.cleaned_data.get("enable_sms"))
            pref.enable_in_app = bool(pref_form.cleaned_data.get("enable_in_app"))
            pref.save(update_fields=["enable_email", "enable_sms", "enable_in_app"])
        else:
            ok = False

        if ok:
            messages.success(request, "Settings updated.")
            return redirect("people:settings")
        messages.error(request, "Please fix the errors below.")

    return render(
        request,
        "people/settings.html",
        {"profile_form": profile_form, "pref_form": pref_form},
    )
