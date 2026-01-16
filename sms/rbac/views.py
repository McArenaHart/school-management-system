from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RoleForm, PermissionForm, AssignRoleForm, AssignPermissionForm, UserCreateForm, BulkUserUploadForm
from .models import Role, Permission, UserRole
from rbac.utils import (
    require_any_perm,
    attach_user_to_role_group,
    detach_user_from_role_group,
    attach_permission_to_role_group,
    detach_permission_from_role_group,
)
from rbac.constants import ROLE_PERMISSIONS, ROLE_PRINCIPAL, ROLE_ADMIN, ROLE_TEACHER, ROLE_PARENT
import csv
from io import TextIOWrapper

User = get_user_model()

def _can_configure(user):
    return user.is_authenticated and (getattr(user, "is_principal", False) or getattr(user, "is_it_admin", False) or getattr(user, "is_school_admin", False) or getattr(user, "is_superuser", False))


ROLE_CANONICAL = {
    "principal": ROLE_PRINCIPAL,
    "school admin": ROLE_ADMIN,
    "admin": ROLE_ADMIN,
    "teacher": ROLE_TEACHER,
    "parent": ROLE_PARENT,
}

@login_required
def rbac_home(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    context = {
        "roles_count": Role.objects.count(),
        "permissions_count": Permission.objects.count(),
        "assignments_count": UserRole.objects.count(),
        "users_with_roles": UserRole.objects.values("user").distinct().count(),
    }
    return render(request, "rbac/home.html", context)

@require_any_perm("rbac.view_role", "auth.view_group")
def roles_list(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    roles = Role.objects.prefetch_related("permissions").order_by("name")
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
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "rbac/roles_form.html", {"form": form, "mode": "create"})

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
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "rbac/roles_form.html", {"form": form, "mode": "edit", "role": role})

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

@require_any_perm("rbac.view_role", "auth.view_group")
def perms_list(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    search = (request.GET.get("q") or "").strip()
    perms = Permission.objects.all()
    if search:
        perms = perms.filter(Q(code__icontains=search) | Q(name__icontains=search))
    perms = perms.order_by("code")
    paginator = Paginator(perms, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "rbac/perms_list.html", {"perms": page_obj.object_list, "page_obj": page_obj, "search": search})

@login_required
@require_http_methods(["GET", "POST"])
def perm_create(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    form = PermissionForm(request.POST or None)
    available_perm_codes = [
        {
            "code": f"{perm.content_type.app_label}.{perm.codename}",
            "name": perm.name,
        }
        for perm in DjangoPermission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    ]
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Permission created.")
        return redirect("rbac:perms_list")
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "rbac/perm_form.html", {"form": form, "available_perm_codes": available_perm_codes})


@login_required
@require_http_methods(["GET", "POST"])
def perm_edit(request, perm_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    perm = get_object_or_404(Permission, id=perm_id)
    form = PermissionForm(request.POST or None, instance=perm)
    available_perm_codes = [
        {
            "code": f"{p.content_type.app_label}.{p.codename}",
            "name": p.name,
        }
        for p in DjangoPermission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    ]
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Permission updated.")
        return redirect("rbac:perms_list")
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")
    return render(request, "rbac/perm_form.html", {"form": form, "available_perm_codes": available_perm_codes, "perm": perm})


@login_required
@require_http_methods(["POST"])
def perm_delete(request, perm_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")
    perm = get_object_or_404(Permission, id=perm_id)
    perm.delete()
    messages.success(request, "Permission deleted.")
    return redirect("rbac:perms_list")


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        role = form.cleaned_data.get("role")
        if role:
            UserRole.objects.get_or_create(user=user, role=role)
            attach_user_to_role_group(user, role.name)
        messages.success(request, "User created.")
        return redirect("rbac:assignments")
    if request.method == "POST" and not form.is_valid():
        messages.error(request, "Fix the form errors.")

    return render(request, "rbac/user_create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def bulk_user_upload(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = BulkUserUploadForm(request.POST or None, request.FILES or None)
    summary = None
    errors = []

    if request.method == "POST" and form.is_valid():
        f = request.FILES.get("csv_file")
        default_password = form.cleaned_data["default_password"]
        created = 0
        updated = 0
        role_attached = 0
        skipped = 0
        roles_created = 0

        try:
            text_wrapper = TextIOWrapper(f.file, encoding="utf-8-sig")
            reader = csv.DictReader(text_wrapper)
            for idx, row in enumerate(reader, start=2):
                username = (row.get("username") or "").strip()
                if not username:
                    skipped += 1
                    errors.append(f"Row {idx}: missing username, skipped.")
                    continue

                defaults = {
                    "email": (row.get("email") or "").strip(),
                    "first_name": (row.get("first_name") or "").strip(),
                    "last_name": (row.get("last_name") or "").strip(),
                }

                user, was_created = User.objects.get_or_create(username=username, defaults=defaults)
                if was_created:
                    user.set_password((row.get("password") or "").strip() or default_password)
                    created += 1
                else:
                    changed = False
                    for field, value in defaults.items():
                        if value and getattr(user, field) != value:
                            setattr(user, field, value)
                            changed = True
                    if changed:
                        updated += 1
                user.save()

                role_label = (row.get("role") or row.get("type") or "").strip()
                if role_label:
                    canonical = ROLE_CANONICAL.get(role_label.lower(), role_label)
                    role = Role.objects.filter(name__iexact=canonical).first()
                    if not role and canonical in ROLE_PERMISSIONS:
                        role = Role.objects.create(name=canonical, description="Auto-created from bulk upload")
                        roles_created += 1
                    if not role:
                        errors.append(f"Row {idx}: role '{role_label}' not found, user created without role.")
                    else:
                        UserRole.objects.get_or_create(user=user, role=role)
                        attach_user_to_role_group(user, role.name)
                        role_attached += 1

            summary = {
                "created": created,
                "updated": updated,
                "role_attached": role_attached,
                "roles_created": roles_created,
                "skipped": skipped,
            }
            messages.success(request, "Import completed.")
        except Exception as exc:
            messages.error(request, f"Import failed: {exc}")

    available_roles = list(Role.objects.order_by("name").values_list("name", flat=True))
    return render(request, "rbac/bulk_user_upload.html", {"form": form, "summary": summary, "errors": errors, "available_roles": available_roles})


@require_any_perm("rbac.view_role", "auth.view_group")
def assignments(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    user_q = (request.GET.get("user_q") or "").strip()
    role_q = (request.GET.get("role_q") or "").strip()
    show_users = request.GET.get("show_users") == "1"

    user_qs = User.objects.all()
    if user_q:
        user_qs = user_qs.filter(
            Q(username__icontains=user_q)
            | Q(first_name__icontains=user_q)
            | Q(last_name__icontains=user_q)
            | Q(email__icontains=user_q)
        )

    role_qs = Role.objects.all()
    if role_q:
        role_qs = role_qs.filter(name__icontains=role_q)

    rows = UserRole.objects.select_related("user", "role")
    if user_q:
        rows = rows.filter(user__in=user_qs)
    if role_q:
        rows = rows.filter(role__in=role_qs)
    rows = rows.order_by("user__username", "role__name")

    rows_page = Paginator(rows, 50).get_page(request.GET.get("page"))

    user_page = None
    if show_users:
        user_page = Paginator(user_qs.order_by("username"), 50).get_page(request.GET.get("user_page"))

    form = AssignRoleForm(user_queryset=user_qs, role_queryset=role_qs)
    return render(
        request,
        "rbac/assignments.html",
        {
            "rows": rows_page.object_list,
            "rows_page": rows_page,
            "form": form,
            "user_q": user_q,
            "role_q": role_q,
            "show_users": show_users,
            "user_page": user_page,
        },
    )

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
        attach_user_to_role_group(user, role.name)
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
    detach_user_from_role_group(ur.user, ur.role.name)
    ur.delete()
    messages.success(request, "Role revoked.")
    return redirect("rbac:assignments")


@require_any_perm("rbac.view_permission", "auth.view_group")
def perm_assignments(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    role_q = (request.GET.get("role_q") or "").strip()
    perm_q = (request.GET.get("perm_q") or "").strip()

    role_qs = Role.objects.all()
    if role_q:
        role_qs = role_qs.filter(name__icontains=role_q)

    perm_qs = Permission.objects.all()
    if perm_q:
        perm_qs = perm_qs.filter(Q(code__icontains=perm_q) | Q(name__icontains=perm_q))

    assignments = Role.permissions.through.objects.select_related("role", "permission")
    if role_q:
        assignments = assignments.filter(role__in=role_qs)
    if perm_q:
        assignments = assignments.filter(permission__in=perm_qs)
    assignments = assignments.order_by("role__name", "permission__code")

    assign_page = Paginator(assignments, 50).get_page(request.GET.get("page"))

    form = AssignPermissionForm(role_queryset=role_qs, permission_queryset=perm_qs)
    context = {
        "assignments": assign_page.object_list,
        "assign_page": assign_page,
        "form": form,
        "role_q": role_q,
        "perm_q": perm_q,
    }
    return render(request, "rbac/perm_assignments.html", context)


@login_required
@require_http_methods(["POST"])
def assign_permission(request):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    form = AssignPermissionForm(request.POST)
    if form.is_valid():
        role = form.cleaned_data["role"]
        perm = form.cleaned_data["permission"]
        role.permissions.add(perm)
        ok, msg = attach_permission_to_role_group(role.name, perm.code)
        if not ok:
            messages.warning(request, f"Assigned to role table but not Django permissions: {msg}")
        messages.success(request, f"Assigned {perm.code} to {role.name}.")
    else:
        messages.error(request, "Fix the form errors.")
    return redirect("rbac:perm_assignments")


@login_required
@require_http_methods(["POST"])
def revoke_permission(request, role_id: int, perm_id: int):
    if not _can_configure(request.user):
        messages.error(request, "Not allowed.")
        return redirect("accounts:dashboard")

    role = get_object_or_404(Role, id=role_id)
    perm = get_object_or_404(Permission, id=perm_id)
    role.permissions.remove(perm)
    detach_permission_from_role_group(role.name, perm.code)
    messages.success(request, f"Removed {perm.code} from {role.name}.")
    return redirect("rbac:perm_assignments")
