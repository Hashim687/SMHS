from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "patient"
        DOCTOR = "doctor"
        NURSE = "nurse"
        ADMIN = "admin"
        LAB = "lab"
        RECEPTION = "reception"
        CASHIER = "cashier"

    STAFF_ROLES = frozenset({"doctor", "nurse", "admin", "lab", "reception", "cashier"})

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.PATIENT, db_index=True)
    staff_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    language = models.CharField(max_length=2, default="en")
    totp_secret = models.CharField(max_length=200, blank=True)
    totp_enabled = models.BooleanField(default=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    @property
    def is_staff_role(self):
        return self.role in self.STAFF_ROLES

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())
