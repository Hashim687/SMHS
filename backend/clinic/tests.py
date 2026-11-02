from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User

from . import triage
from .models import Patient, Ticket

PT = {"kind": "opd", "name": "Ali Khan", "phone": "9876543210", "age": 40, "sex": "m"}


@override_settings(DEBUG=True, RAZORPAY_KEY_ID="")
class Flow(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed")
        triage.invalidate()
        self.c = APIClient()

    def pay(self, **kw):
        o = self.c.post("/api/public/tickets", {**PT, **kw}, format="json").json()
        r = self.c.post(f"/api/public/tickets/{o['ref']}/verify",
                        {"razorpay_payment_id": o["mock_payment_id"], "razorpay_signature": o["mock_signature"]}, format="json")
        return o, r

    def test_pay_then_triage(self):
        o, r = self.pay()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["patient_uid"].startswith("SMHS"))
        r = self.c.post(f"/api/public/tickets/{o['ref']}/symptoms", {"symptoms": ["chest_pain", "breathless"]}, format="json").json()
        self.assertEqual(r["department"]["code"], "CARDIO")
        self.assertTrue(r["escalate"])
        self.assertEqual(r["token_no"], 1)

    def test_forged_signature(self):
        o = self.c.post("/api/public/tickets", PT, format="json").json()
        r = self.c.post(f"/api/public/tickets/{o['ref']}/verify", {"razorpay_payment_id": "x", "razorpay_signature": "y"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post(f"/api/public/tickets/{o['ref']}/symptoms", {"symptoms": ["fever"]}, format="json")
        self.assertEqual(r.status_code, 402)

    def test_same_patient_same_id(self):
        a = self.pay()[1].json()["patient_uid"]
        b = self.pay()[1].json()["patient_uid"]
        self.assertEqual(a, b)
        self.assertEqual(Patient.objects.count(), 1)

    def test_child_goes_paediatrics(self):
        o, _ = self.pay(age=5)
        r = self.c.post(f"/api/public/tickets/{o['ref']}/symptoms", {"symptoms": ["fever"]}, format="json").json()
        self.assertEqual(r["department"]["code"], "PAED")

    def test_unknown_symptom_and_bad_phone(self):
        o, _ = self.pay()
        self.assertEqual(self.c.post(f"/api/public/tickets/{o['ref']}/symptoms", {"symptoms": ["zzz"]}, format="json").status_code, 400)
        self.assertEqual(self.c.post("/api/public/tickets", {**PT, "phone": "123"}, format="json").status_code, 400)

    def test_emergency_queue_priority(self):
        for name, syms, phone in (("Amir", ["abdominal_pain"], "9111111111"), ("Bashir", ["bleeding", "fracture"], "9222222222"), ("Chand", ["chest_pain"], "9333333333")):
            o, _ = self.pay(kind="emergency", name=name, phone=phone)
            r = self.c.post(f"/api/public/tickets/{o['ref']}/symptoms", {"symptoms": syms}, format="json").json()
            if name == "Bashir":
                self.assertEqual((r["department"]["code"], r["priority"], r["category"]), ("EMERG_SURG", 1, "surgical"))
        User.objects.create_user("n1", password="Str0ng-Pass-123", role="nurse")
        t = self.c.post("/api/auth/login", {"username": "n1", "password": "Str0ng-Pass-123"}, format="json").json()["access"]
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + t)
        q = self.c.get("/api/staff/emergency-queue").json()
        self.assertEqual([x["name"] for x in q], ["Bashir", "Chand", "Amir"])

    def test_cash_and_roles(self):
        User.objects.create_user("rc", password="Str0ng-Pass-123", role="reception")
        User.objects.create_user("dr", password="Str0ng-Pass-123", role="doctor")
        t = self.c.post("/api/auth/login", {"username": "dr", "password": "Str0ng-Pass-123"}, format="json").json()["access"]
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + t)
        self.assertEqual(self.c.post("/api/staff/tickets/cash", PT, format="json").status_code, 403)
        t = self.c.post("/api/auth/login", {"username": "rc", "password": "Str0ng-Pass-123"}, format="json").json()["access"]
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + t)
        r = self.c.post("/api/staff/tickets/cash", PT, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Ticket.objects.get(ref=r.json()["ref"]).status, "paid")

    def test_price_floor(self):
        User.objects.create_user("ad", password="Str0ng-Pass-123", role="admin")
        t = self.c.post("/api/auth/login", {"username": "ad", "password": "Str0ng-Pass-123"}, format="json").json()["access"]
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + t)
        self.assertEqual(self.c.patch("/api/admin/prices/opd/", {"amount": "5"}, format="json").status_code, 400)
        self.assertEqual(self.c.patch("/api/admin/prices/opd/", {"amount": "25"}, format="json").status_code, 200)
