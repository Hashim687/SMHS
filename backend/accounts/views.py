from datetime import timedelta

import pyotp
from django.conf import settings
from django.core import signing
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import AuditLog, record
from smhs.pagination import Pg

from .crypto import decrypt, encrypt
from .models import User
from .permissions import role_required
from .serializers import LoginSerializer, OtpSerializer, UserSerializer

signer = signing.TimestampSigner(salt="mfa")
IsAdmin = role_required("admin")


def issue(user, enroll=False):
    r = RefreshToken.for_user(user)
    r["role"] = user.role
    return {"access": str(r.access_token), "refresh": str(r), "role": user.role,
            "language": user.language, "enroll_required": enroll}


def fail(user, request, reason):
    user.failed_attempts += 1
    if user.failed_attempts >= settings.MAX_FAILED_LOGINS:
        user.locked_until = timezone.now() + timedelta(minutes=settings.LOCKOUT_MINUTES)
        user.failed_attempts = 0
    user.save(update_fields=["failed_attempts", "locked_until"])
    record(request, "login_failed", user, reason)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        u = User.objects.filter(username=s.validated_data["username"], is_active=True).first()
        if u and u.is_locked:
            record(request, "login_locked", u, "")
            return Response({"detail": "locked"}, status=423)
        if not u or not u.check_password(s.validated_data["password"]):
            if u:
                fail(u, request, "password")
            else:
                record(request, "login_failed", None, "unknown_user")
            return Response({"detail": "invalid"}, status=401)
        u.failed_attempts = 0
        u.save(update_fields=["failed_attempts"])
        if u.is_staff_role and u.totp_enabled:
            return Response({"mfa_required": True, "mfa_token": signer.sign(str(u.pk))})
        record(request, "login_ok", u, "")
        return Response(issue(u, enroll=u.is_staff_role))


class OtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "otp"

    def post(self, request):
        s = OtpSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            pk = signer.unsign(s.validated_data["mfa_token"], max_age=300)
        except signing.BadSignature:
            return Response({"detail": "invalid"}, status=401)
        u = User.objects.filter(pk=pk, is_active=True, totp_enabled=True).first()
        if not u or u.is_locked:
            return Response({"detail": "invalid"}, status=401)
        if not pyotp.TOTP(decrypt(u.totp_secret)).verify(s.validated_data["code"], valid_window=1):
            fail(u, request, "otp")
            return Response({"detail": "invalid"}, status=401)
        record(request, "login_ok_2fa", u, "")
        return Response(issue(u))


class TwoFASetupView(APIView):
    def post(self, request):
        u = request.user
        if not u.is_staff_role or u.totp_enabled:
            return Response({"detail": "n/a"}, status=400)
        secret = pyotp.random_base32()
        u.totp_secret = encrypt(secret)
        u.save(update_fields=["totp_secret"])
        return Response({"secret": secret,
                         "uri": pyotp.TOTP(secret).provisioning_uri(u.username, issuer_name="SMHS Srinagar")})


class TwoFAConfirmView(APIView):
    throttle_scope = "otp"

    def post(self, request):
        u = request.user
        code = str(request.data.get("code", ""))
        if not u.totp_secret or u.totp_enabled or not pyotp.TOTP(decrypt(u.totp_secret)).verify(code, valid_window=1):
            return Response({"detail": "invalid"}, status=400)
        u.totp_enabled = True
        u.save(update_fields=["totp_enabled"])
        record(request, "2fa_enabled", u, "")
        return Response({"totp_enabled": True})


class MeView(APIView):
    def get(self, request):
        u = request.user
        return Response({"id": u.id, "username": u.username, "role": u.role, "language": u.language,
                         "totp_enabled": u.totp_enabled, "enroll_required": u.is_staff_role and not u.totp_enabled})


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.order_by("id")

    def perform_destroy(self, inst):
        inst.is_active = False
        inst.save(update_fields=["is_active"])

    @action(detail=True, methods=["post"])
    def reset_2fa(self, request, pk=None):
        u = self.get_object()
        u.totp_secret, u.totp_enabled, u.failed_attempts, u.locked_until = "", False, 0, None
        u.save()
        return Response({"ok": True})


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = AuditSerializer
    pagination_class = Pg
    queryset = AuditLog.objects.order_by("-id")
