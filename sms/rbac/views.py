from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RoleForm, PermissionForm, AssignRoleForm
from .models import Role, Permission, UserRole

User = get_user_model()

def _can_configure(user):
    return user.is_authenticated and (getattr(user, "is_principal", False) or getattr(user, "is_it_admin", False) or getattr(user, "is_school_admin", False) or getattr(user, "is_superuser", False))

@login_required
def rbac_home(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    return render(request, "rbac/home.html")

@login_required
def roles_list(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    roles = Role.objects.all().order_by("name")
    return render(request, "rbac/roles_list.html", {"roles": roles})

@login_required
@require_http_methods(["GET", "POST"])
def role_create(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    form = RoleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Role created.")
        return redirect("rbac:roles_list")
    return render(request, "rbac/role_form.html", {"form": form, "mode": "create"})

@login_required
@require_http_methods(["GET", "POST"])
def role_edit(request, role_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    role = get_object_or_404(Role, id=role_id)
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Role updated.")
        return redirect("rbac:roles_list")
    return render(request, "rbac/role_form.html", {"form": form, "mode": "edit", "role": role})

@login_required
@require_http_methods(["POST"])
def role_delete(request, role_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    role = get_object_or_404(Role, id=role_id)
    role.delete()
    messages.success(request, "Role deleted.")
    return redirect("rbac:roles_list")

@login_required
def perms_list(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    perms = Permission.objects.all().order_by("code")
    return render(request, "rbac/perms_list.html", {"perms": perms})

@login_required
@require_http_methods(["GET", "POST"])
def perm_create(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    form = PermissionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Permission created.")
        return redirect("rbac:perms_list")
    return render(request, "rbac/perm_form.html", {"form": form})

@login_required
def assignments(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    rows = UserRole.objects.select_related("user", "role").order_by("user__username", "role__name")[:500]
    form = AssignRoleForm()
    return render(request, "rbac/assignments.html", {"rows": rows, "form": form})

@login_required
@require_http_methods(["POST"])
def assign_role(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = AssignRoleForm(request.POST)
    if form.is_valid():
        user = form.cleaned_data["user"]
        role = form.cleaned_data["role"]
        UserRole.objects.get_or_create(user=user, role=role)
        messages.success(request, f"Assigned {role} to {user}.")
    else:
        messages.error(request, "Fix the form errors.")
    return redirect("rbac:assignments")

@login_required
@require_http_methods(["POST"])
def revoke_role(request, user_role_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    ur = get_object_or_404(UserRole, id=user_role_id)
    ur.delete()
    messages.success(request, "Role revoked.")
    return redirect("rbac:assignments")
