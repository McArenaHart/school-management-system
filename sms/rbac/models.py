from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

class Permission(models.Model):
    code = models.CharField(max_length=120, unique=True)  # e.g. "finance.verify_pop"
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.code

class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)   # e.g. "Principal", "Registrar"
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    def __str__(self):
        return self.name

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rbac_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="users")

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user} -> {self.role}"
