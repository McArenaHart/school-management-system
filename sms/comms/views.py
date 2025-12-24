from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from people.models import Student
from .forms import StartThreadForm, MessageForm
from .models import Thread, Message, ThreadReadState
from .utils import can_view_thread
from .services_notify import notify_user


def _threads_for_user(u):
    if u.is_teacher:
        return Thread.objects.filter(teacher_user=u)
    if u.is_parent:
        return Thread.objects.filter(parent_user=u)
    return Thread.objects.all()


@login_required
def inbox(request):
    u = request.user
    q = (request.GET.get("q") or "").strip()

    threads = _threads_for_user(u).select_related("student", "teacher_user", "parent_user")

    if q:
        threads = threads.filter(
            Q(student__student_id__icontains=q) |
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) |
            Q(teacher_user__username__icontains=q) |
            Q(parent_user__username__icontains=q)
        )

    # last message time for ordering
    threads = threads.annotate(last_msg_at=Max("messages__created_at")).order_by("-last_msg_at", "-created_at")

    # prepare unread counts
    thread_ids = list(threads.values_list("id", flat=True))
    read_map = {
        rs.thread_id: rs.last_read_at
        for rs in ThreadReadState.objects.filter(user=u, thread_id__in=thread_ids)
    }

    last_msg_map = {
        m.thread_id: m
        for m in Message.objects.filter(thread_id__in=thread_ids)
                           .select_related("sender")
                           .order_by("thread_id", "-created_at")
                           .distinct("thread_id")
    } if Message._meta.managed and Message.objects.model._meta.db_table else {}

    # portable fallback without distinct("thread_id") if your DB is sqlite:
    last_msg_map = {}
    for tid in thread_ids:
        lm = Message.objects.filter(thread_id=tid).select_related("sender").order_by("-created_at").first()
        if lm:
            last_msg_map[tid] = lm

    unread = {}
    for t in threads:
        last_read = read_map.get(t.id)
        base = Message.objects.filter(thread=t).exclude(sender=u)
        if last_read:
            base = base.filter(created_at__gt=last_read)
        unread[t.id] = base.count()

    return render(
        request,
        "comms/inbox.html",
        {"threads": threads, "q": q, "unread": unread, "last_msg_map": last_msg_map},
    )


@login_required
@require_http_methods(["GET", "POST"])
def start_thread(request):
    if not (request.user.is_teacher or request.user.is_school_admin or request.user.is_principal):
        return redirect("comms:inbox")

    form = StartThreadForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        sid = form.cleaned_data["student_id"].strip()
        parent_username = form.cleaned_data["parent_username"].strip()

        student = get_object_or_404(Student, student_id__iexact=sid)
        parent_user = get_object_or_404(type(request.user), username=parent_username)

        if parent_user not in student.parent_users.all():
            messages.error(request, "That parent is not linked to this student.")
            return render(request, "comms/start_thread.html", {"form": form})

        if not request.user.is_teacher:
            messages.error(request, "For MVP, start threads from a teacher account.")
            return render(request, "comms/start_thread.html", {"form": form})

        thread, _ = Thread.objects.get_or_create(
            student=student,
            teacher_user=request.user,
            parent_user=parent_user,
        )
        return redirect("comms:thread_detail", thread_id=thread.id)

    return render(request, "comms/start_thread.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def thread_detail(request, thread_id: int):
    thread = get_object_or_404(Thread.objects.select_related("student", "teacher_user", "parent_user"), id=thread_id)

    if not can_view_thread(request.user, thread):
        return redirect("comms:inbox")

    # mark as read on view (GET) and after sending (POST)
    ThreadReadState.objects.update_or_create(
        thread=thread,
        user=request.user,
        defaults={"last_read_at": timezone.now()},
    )

    form = MessageForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        body = form.cleaned_data["body"].strip()
        Message.objects.create(thread=thread, sender=request.user, body=body)

        other = thread.parent_user if request.user == thread.teacher_user else thread.teacher_user
        notify_user(other, subject="SMS: New message", body=body[:300])

        ThreadReadState.objects.update_or_create(
            thread=thread, user=request.user, defaults={"last_read_at": timezone.now()}
        )

        return redirect("comms:thread_detail", thread_id=thread.id)

    messages_qs = thread.messages.select_related("sender").order_by("created_at")
    return render(
        request,
        "comms/thread.html",
        {"thread": thread, "form": form, "messages_qs": messages_qs},
    )
