from .models import Permission

def user_has_perm(user, perm_code: str) -> bool:
    if not user.is_authenticated:
        return False
    # allow superusers / principals / IT admins to bypass if you want:
    if getattr(user, "is_superuser", False) or getattr(user, "is_principal", False) or getattr(user, "is_it_admin", False):
        return True

    return user.rbac_roles.filter(role__permissions__code=perm_code).exists()
