from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Roles from document: admin, parent, principal, teacher :contentReference[oaicite:2]{index=2}
    is_principal = models.BooleanField(default=False)
    is_school_admin = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_parent = models.BooleanField(default=False)

    def primary_role(self) -> str:
        if self.is_principal:
            return "principal"
        if self.is_school_admin:
            return "admin"
        if self.is_teacher:
            return "teacher"
        if self.is_parent:
            return "parent"
        return "user"
