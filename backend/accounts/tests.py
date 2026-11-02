import pyotp
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .crypto import decrypt
from .models import User

PW = "Str0ng-Pass-123"


class AuthFlow(TestCase):
    def setUp(self):
        cache.clear()
        self.c = APIClient()
        self.u = User.objects.create_user("dr1", password=PW, role="doctor", staff_id="D1")
        User.objects.create_user("adm", password=PW, role="admin")

    def login(self, name):
        return self.c.post("/api/auth/login", {"username": name, "password": PW}, format="json")

    def totp(self):
        return pyotp.TOTP(decrypt(User.objects.get(pk=self.u.pk).totp_secret)).now()

    def test_enroll_then_otp(self):
        r = self.login("dr1").json()
        self.assertTrue(r["enroll_required"])
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + r["access"])
        self.assertEqual(self.c.post("/api/auth/2fa/setup").status_code, 200)
        self.assertEqual(self.c.post("/api/auth/2fa/confirm", {"code": self.totp()}, format="json").status_code, 200)
        self.c.credentials()
        r = self.login("dr1").json()
        self.assertTrue(r["mfa_required"])
        r = self.c.post("/api/auth/otp", {"mfa_token": r["mfa_token"], "code": self.totp()}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.json())

    def test_lockout(self):
        for _ in range(5):
            self.c.post("/api/auth/login", {"username": "dr1", "password": "bad"}, format="json")
        self.assertEqual(self.login("dr1").status_code, 423)

    def test_rbac(self):
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + self.login("dr1").json()["access"])
        self.assertEqual(self.c.get("/api/admin/users/").status_code, 403)
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + self.login("adm").json()["access"])
        self.assertEqual(self.c.get("/api/admin/users/").status_code, 200)
