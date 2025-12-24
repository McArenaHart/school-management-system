from decimal import Decimal
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from people.models import Student
from .models import (
    Enrollment, TimetableEntry, AttendanceRecord,
    Assessment, Grade, ClassGroup, Subject
)
from .forms import AttendancePickForm, AssessmentFilterForm, CreateAssessmentForm
from .models import ClassGroup, Enrollment, TimetableEntry, AttendanceRecord, Assessment, Grade


ATTENDANCE_STATUS = ["present", "absent", "late"]


def _staff_can(u):
    return u.is_authenticated and (u.is_teacher or u.is_school_admin or u.is_principal)

@login_required
def teacher_home(request):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    today = timezone.localdate()
    weekday = today.weekday()  # 0=Mon
    entries = TimetableEntry.objects.filter(teacher_user=request.user, day_of_week=weekday)\
        .select_related("class_group", "subject").order_by("start_time")

    # quick class list from timetable
    class_ids = list(entries.values_list("class_group_id", flat=True))
    classes = ClassGroup.objects.filter(id__in=class_ids).order_by("name")

    return render(request, "academics/teacher_home.html", {
        "today": today,
        "entries": entries,
        "classes": classes,
    })

@login_required
def teacher_classes(request):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    # classes taught by this teacher (from timetable)
    class_ids = TimetableEntry.objects.filter(teacher_user=request.user).values_list("class_group_id", flat=True).distinct()
    classes = ClassGroup.objects.filter(id__in=class_ids).order_by("name")

    return render(request, "academics/teacher_classes.html", {"classes": classes})

@login_required
def class_detail(request, class_group_id: int):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    class_group = get_object_or_404(ClassGroup, id=class_group_id)
    # confirm teacher actually teaches this class (from timetable)
    if not TimetableEntry.objects.filter(class_group=class_group, teacher_user=request.user).exists():
        messages.error(request, "You are not assigned to this class.")
        return redirect("academics:teacher_classes")

    roster = Enrollment.objects.filter(class_group=class_group).select_related("student").order_by("student__last_name", "student__first_name")

    return render(request, "academics/class_detail.html", {"class_group": class_group, "roster": roster})

@login_required
@require_http_methods(["GET", "POST"])
def take_attendance_pick(request):
    if not _staff_can(request.user):
        return redirect("accounts:dashboard")

    form = AttendancePickForm(request.POST or None)
    if request.method == "GET":
        return render(request, "academics/take_attendance_pick.html", {"form": form})

    if form.is_valid():
        cg = form.cleaned_data["class_group"]
        d = form.cleaned_data["date"] or timezone.localdate()
        return redirect(f"/academics/attendance/take/mark/?class_group_id={cg.id}&date={d.isoformat()}")

    return render(request, "academics/take_attendance_pick.html", {"form": form})

@login_required
@require_http_methods(["GET", "POST"])
def take_attendance_mark(request):
    if not _staff_can(request.user):
        return redirect("accounts:dashboard")

    class_group_id = request.GET.get("class_group_id") if request.method == "GET" else request.POST.get("class_group_id")
    date_str = request.GET.get("date") if request.method == "GET" else request.POST.get("date")
    if not class_group_id or not date_str:
        return redirect("academics:take_attendance_pick")

    attendance_date = date.fromisoformat(date_str)
    class_group = get_object_or_404(ClassGroup, id=class_group_id)

    enrollments = Enrollment.objects.filter(class_group=class_group).select_related("student")\
        .order_by("student__last_name", "student__first_name")

    existing_map = {
        ar.student_id: ar
        for ar in AttendanceRecord.objects.filter(class_group=class_group, date=attendance_date)
    }

    if request.method == "GET":
        return render(request, "academics/take_attendance_mark.html", {
            "class_group": class_group,
            "attendance_date": attendance_date,
            "enrollments": enrollments,
            "existing_map": existing_map,
            "status_choices": ATTENDANCE_STATUS,
        })

    with transaction.atomic():
        for enr in enrollments:
            status = request.POST.get(f"status_{enr.student.id}", "present")
            if status not in ATTENDANCE_STATUS:
                status = "present"
            AttendanceRecord.objects.update_or_create(
                student=enr.student, class_group=class_group, date=attendance_date,
                defaults={"status": status, "recorded_by": request.user}
            )

    messages.success(request, f"Attendance saved: {class_group} · {attendance_date}")
    return redirect(f"/academics/attendance/take/mark/?class_group_id={class_group.id}&date={attendance_date.isoformat()}")

@login_required
def teacher_assessments(request):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    form = AssessmentFilterForm(request.GET)
    qs = Assessment.objects.filter(teacher_user=request.user).select_related("class_group", "subject").order_by("-date")

    q = ""
    if form.is_valid():
        q = form.cleaned_data.get("q") or ""
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(subject__name__icontains=q) |
                Q(subject__code__icontains=q) |
                Q(class_group__name__icontains=q)
            )

    return render(request, "academics/teacher_assessments.html", {"assessments": qs[:200], "form": form, "q": q})

@login_required
@require_http_methods(["GET", "POST"])
def create_assessment(request):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    form = CreateAssessmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        cg = form.cleaned_data["class_group"]
        subject = form.cleaned_data["subject"]
        title = form.cleaned_data["title"].strip()
        typ = form.cleaned_data["type"]
        d = form.cleaned_data["date"] or timezone.localdate()
        max_score = form.cleaned_data["max_score"]
        weight = form.cleaned_data["weight"]

        Assessment.objects.create(
            class_group=cg,
            subject=subject,
            teacher_user=request.user,
            title=title,
            type=typ,
            date=d,
            max_score=max_score,
            weight=weight,
        )
        messages.success(request, "Assessment created.")
        return redirect("academics:teacher_assessments")

    return render(request, "academics/create_assessment.html", {"form": form})

@login_required
def parent_student_hub(request):
    if not request.user.is_parent:
        return redirect("accounts:dashboard")

    student = request.user.linked_students.first()
    if not student:
        return render(request, "academics/parent_student_hub.html", {"note": "No linked student."})

    # timetable = class timetable for student
    enr = Enrollment.objects.filter(student=student).select_related("class_group").first()
    timetable = TimetableEntry.objects.filter(class_group=enr.class_group).select_related("subject").order_by("day_of_week", "start_time") if enr else TimetableEntry.objects.none()

    attendance = AttendanceRecord.objects.filter(student=student).select_related("class_group").order_by("-date")[:30]
    grades = Grade.objects.filter(student=student).select_related("assessment", "assessment__subject").order_by("-assessment__date")[:40]

    return render(request, "academics/parent_student_hub.html", {
        "student": student,
        "enrollment": enr,
        "timetable": timetable,
        "attendance": attendance,
        "grades": grades,
    })

@login_required
def my_timetable(request):
    u = request.user

    if u.is_teacher:
        entries = TimetableEntry.objects.filter(teacher_user=u).select_related("class_group", "subject")
        title = "My Timetable (Teacher)"
    elif u.is_parent:
        student = u.linked_students.first()
        if not student:
            return render(request, "academics/my_timetable.html", {"entries": [], "title": "Timetable", "note": "No linked student."})
        enr = Enrollment.objects.filter(student=student).select_related("class_group").first()
        entries = TimetableEntry.objects.filter(class_group=enr.class_group).select_related("class_group", "subject") if enr else TimetableEntry.objects.none()
        title = f"Timetable ({student.first_name} {student.last_name})"
    else:
        entries = TimetableEntry.objects.all().select_related("class_group", "subject")
        title = "All Timetables"

    return render(request, "academics/my_timetable.html", {"entries": entries, "title": title})

@login_required
def my_attendance(request):
    u = request.user
    student = u.linked_students.first() if u.is_parent else None

    if not student:
        return render(request, "academics/my_attendance.html", {"records": [], "note": "No linked student."})

    records = AttendanceRecord.objects.filter(student=student).select_related("class_group").order_by("-date")[:60]
    return render(request, "academics/my_attendance.html", {"records": records, "student": student})


@login_required
@require_http_methods(["GET", "POST"])
def enter_grades(request, assessment_id: int):
    if not request.user.is_teacher:
        return redirect("accounts:dashboard")

    assessment = get_object_or_404(Assessment, id=assessment_id, teacher_user=request.user)
    enrollments = Enrollment.objects.filter(class_group=assessment.class_group).select_related("student").order_by("student__last_name", "student__first_name")

    if request.method == "GET":
        existing = {g.student_id: g for g in Grade.objects.filter(assessment=assessment)}
        return render(request, "academics/enter_grades.html", {"assessment": assessment, "enrollments": enrollments, "existing": existing})

    with transaction.atomic():
        for enr in enrollments:
            score_str = request.POST.get(f"score_{enr.student.id}", "").strip()
            comment = request.POST.get(f"comment_{enr.student.id}", "").strip()
            if score_str == "":
                continue
            Grade.objects.update_or_create(
                assessment=assessment,
                student=enr.student,
                defaults={"score": score_str, "comment": comment},
            )

    messages.success(request, "Grades saved.")
    return redirect("academics:teacher_assessments")

@login_required
def my_grades(request):
    u = request.user
    student = u.linked_students.first() if u.is_parent else None

    if not student:
        return render(request, "academics/my_grades.html", {"grades": [], "note": "No linked student."})

    grades = Grade.objects.filter(student=student).select_related("assessment", "assessment__subject").order_by("-assessment__date")[:80]
    return render(request, "academics/my_grades.html", {"grades": grades, "student": student})

@login_required
def parent_student_hub(request):
    if not request.user.is_parent:
        return redirect("accounts:dashboard")

    student = request.user.linked_students.first()
    if not student:
        return render(request, "academics/parent_student_hub.html", {"note": "No linked student."})

    # timetable = class timetable for student
    enr = Enrollment.objects.filter(student=student).select_related("class_group").first()
    timetable = TimetableEntry.objects.filter(class_group=enr.class_group).select_related("subject").order_by("day_of_week", "start_time") if enr else TimetableEntry.objects.none()

    attendance = AttendanceRecord.objects.filter(student=student).select_related("class_group").order_by("-date")[:30]
    grades = Grade.objects.filter(student=student).select_related("assessment", "assessment__subject").order_by("-assessment__date")[:40]

    return render(request, "academics/parent_student_hub.html", {
        "student": student,
        "enrollment": enr,
        "timetable": timetable,
        "attendance": attendance,
        "grades": grades,
    })
