from django.urls import path
from .views import (
    rbac_home,
    roles_list, role_create, role_edit, role_delete,
    perms_list, perm_create,
    assignments, assign_role, revoke_role,
)

app_name = "rbac"

urlpatterns = [
    path("", rbac_home, name="home"),

    path("roles/", roles_list, name="roles_list"),
    path("roles/create/", role_create, name="role_create"),
    path("roles/<int:role_id>/edit/", role_edit, name="role_edit"),
    path("roles/<int:role_id>/delete/", role_delete, name="role_delete"),

    path("permissions/", perms_list, name="perms_list"),
    path("permissions/create/", perm_create, name="perm_create"),

    path("assignments/", assignments, name="assignments"),
    path("assign/", assign_role, name="assign_role"),
    path("revoke/<int:user_role_id>/", revoke_role, name="revoke_role"),
]
