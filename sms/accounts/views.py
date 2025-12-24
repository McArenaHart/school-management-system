from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from people.models import Student, TeacherProfile
from finance.models import FeeInvoice
from comms.models import Thread, Message, NotificationLog

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("accounts:dashboard")
        error = "Invalid username/password."
    return render(request, "accounts/login.html", {"error": error})

def logout_view(request):
    logout(request)
    return redirect("accounts:login")

@login_required
def dashboard(request):
    role = request.user.primary_role()
    ctx = {"role": role}

    if role in ("principal", "admin"):
        ctx.update({
            "students_count": Student.objects.count(),
            "teachers_count": TeacherProfile.objects.count(),
            "unpaid_invoices": FeeInvoice.objects.filter(status__in=["unpaid", "partial", "pending_verification"]).count(),
            "threads_count": Thread.objects.count(),
            "notifications": NotificationLog.objects.order_by("-created_at")[:10],
        })

    if role == "teacher":
        ctx.update({
            "my_threads": Thread.objects.filter(teacher_user=request.user).count(),
            "my_sent_messages": Message.objects.filter(sender=request.user).count(),
        })

    if role == "parent":
        ctx.update({
            "linked_students": request.user.linked_students.all(),
            "my_invoices": FeeInvoice.objects.filter(parent_user=request.user).count(),
            "my_threads": Thread.objects.filter(parent_user=request.user).count(),
        })

    return render(request, "accounts/dashboard.html", ctx)
