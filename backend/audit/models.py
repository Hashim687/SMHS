from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40, db_index=True)
    method = models.CharField(max_length=8, blank=True)
    path = models.CharField(max_length=255, blank=True)
    status = models.PositiveSmallIntegerField(null=True)
    ip = models.GenericIPAddressField(null=True)
    detail = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    def save(self, *a, **k):
        if self.pk:
            raise PermissionError
        super().save(*a, **k)

    def delete(self, *a, **k):
        raise PermissionError


def record(request, action, user=None, detail="", status=None):
    ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
    AuditLog.objects.create(user=user, action=action, method=request.method, path=request.path[:255],
                            status=status, ip=ip, detail=detail[:255])
