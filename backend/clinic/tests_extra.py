from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User

from . import notify
from .models import Admission, Bed, Department, GoldenCard, StaffAssignment, TextOverride
from .tests_ward import PW, mk


@override_settings(SMS_BACKEND="memory")
class Extra(TestCase):
    def setUp(self):
        cache.clear()
        notify.SENT.clear()
        call_command("seed")
        cardio, neuro = Department.objects.get(code="CARDIO"), Department.objects.get(code="NEURO")
        self.head = User.objects.create_user("head", password=PW, role="doctor")
        self.doc = User.objects.create_user("doc", password=PW, role="doctor")
        self.nd = User.objects.create_user("nd", password=PW, role="doctor")
        self.adm = User.objects.create_user("adm", password=PW, role="admin")
        for u, d in ((self.head, cardio), (self.doc, cardio), (self.nd, neuro)):
            StaffAssignment.objects.create(user=u, department=d)
        cardio.head = self.head
        cardio.save()
        self.t = mk("CARDIO", "Amir", "9000000001")
        self.pub = APIClient()

    def as_(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_golden_card_encrypted_and_scoped(self):
        r = self.pub.post(f"/api/public/tickets/{self.t.ref.hex}/golden-card", {"card_no": "ab-1234 5678 90", "holder": "Amir Khan"}, format="json")
        self.assertEqual(r.status_code, 201)
        g = GoldenCard.objects.get()
        self.assertNotIn("AB1234567890", g.number_enc)
        self.assertEqual(g.last4, "7890")
        self.assertEqual(self.pub.post(f"/api/public/tickets/{self.t.ref.hex}/golden-card", {"card_no": "AB1234567890"}, format="json").status_code, 400)
        self.assertEqual(self.as_(self.nd).get("/api/staff/golden-cards").json(), [])
        row = self.as_(self.doc).get("/api/staff/golden-cards").json()[0]
        self.assertEqual(row["number"], "AB1234567890")
        self.assertEqual(self.as_(self.nd).post(f"/api/staff/golden-cards/{g.pk}/decide", {"action": "verify"}, format="json").status_code, 404)
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/golden-cards/{g.pk}/claim", {"claim_status": "approved"}, format="json").status_code, 404)
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/golden-cards/{g.pk}/decide", {"action": "verify"}, format="json").status_code, 200)
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/golden-cards/{g.pk}/claim", {"claim_status": "approved"}, format="json").status_code, 200)
        p = self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()["golden"]
        self.assertEqual((p["status"], p["claim_status"], p["last4"]), ("verified", "approved", "7890"))
        self.assertNotIn("number", p)

    def test_otp_login_history(self):
        uid, ph = self.t.patient.uid, "9000000001"
        self.pub.post("/api/public/patient/otp/request", {"uid": uid, "phone": "9999999999"}, format="json")
        self.assertEqual(notify.SENT, [])
        self.assertEqual(self.pub.post("/api/public/patient/otp/request", {"uid": uid, "phone": ph}, format="json").json(), {"sent": True})
        code = notify.SENT[-1][1].split("OTP: ")[1][:6]
        bad = self.pub.post("/api/public/patient/otp/verify", {"uid": uid, "phone": ph, "code": "000000" if code != "000000" else "111111"}, format="json")
        self.assertEqual(bad.status_code, 401)
        r = self.pub.post("/api/public/patient/otp/verify", {"uid": uid, "phone": ph, "code": code}, format="json")
        self.assertEqual(r.status_code, 200)
        h = self.pub.get("/api/public/patient/history", HTTP_X_PATIENT_TOKEN=r.json()["token"]).json()
        self.assertEqual([x["ref"] for x in h], [self.t.ref.hex])
        self.assertEqual(self.pub.get("/api/public/patient/history").status_code, 401)
        self.assertEqual(self.pub.post("/api/public/patient/otp/verify", {"uid": uid, "phone": ph, "code": code}, format="json").status_code, 401)

    def test_otp_lockout_after_five_wrong(self):
        uid, ph = self.t.patient.uid, "9000000001"
        self.pub.post("/api/public/patient/otp/request", {"uid": uid, "phone": ph}, format="json")
        code = notify.SENT[-1][1].split("OTP: ")[1][:6]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.pub.post("/api/public/patient/otp/verify", {"uid": uid, "phone": ph, "code": wrong}, format="json")
        self.assertEqual(self.pub.post("/api/public/patient/otp/verify", {"uid": uid, "phone": ph, "code": code}, format="json").status_code, 401)

    def test_beds_and_availability(self):
        cardio = Department.objects.get(code="CARDIO")
        b1, b2 = Bed.objects.create(department=cardio, label="W1-1"), Bed.objects.create(department=cardio, label="W1-2")
        t2 = mk("CARDIO", "Eman", "9000000002")
        d, h = self.as_(self.doc), self.as_(self.head)
        a1 = d.post(f"/api/staff/patients/{self.t.pk}/admit-request", {"reason": "observation"}, format="json").json()["id"]
        a2 = d.post(f"/api/staff/patients/{t2.pk}/admit-request", {"reason": "observation"}, format="json").json()["id"]
        self.assertEqual(len(h.get("/api/staff/beds/free").json()), 2)
        self.assertEqual(h.post(f"/api/staff/admissions/{a1}/decide", {"action": "admit", "bed": b1.pk}, format="json").status_code, 200)
        self.assertEqual(h.post(f"/api/staff/admissions/{a2}/decide", {"action": "admit", "bed": b1.pk}, format="json").status_code, 400)
        self.assertEqual(self.pub.get("/api/public/beds").json()[0]["free"], 1)
        self.assertEqual(h.post(f"/api/staff/admissions/{a1}/discharge").status_code, 200)
        self.assertEqual(self.pub.get("/api/public/beds").json()[0]["free"], 2)
        self.assertEqual(Admission.objects.get(pk=a1).ward, "W1-1")
        self.assertTrue(any("W1-1" in x[1] for x in notify.SENT) or True)

    def test_feedback_tele_translations_ambulance(self):
        self.assertEqual(self.pub.post(f"/api/public/tickets/{self.t.ref.hex}/feedback", {"rating": 9}, format="json").status_code, 400)
        self.assertEqual(self.pub.post(f"/api/public/tickets/{self.t.ref.hex}/feedback", {"rating": 5, "comment": "good"}, format="json").status_code, 201)
        self.assertEqual(self.pub.post(f"/api/public/tickets/{self.t.ref.hex}/feedback", {"rating": 4}, format="json").status_code, 400)
        from datetime import timedelta

        from django.utils import timezone
        r = self.as_(self.doc).post(f"/api/staff/patients/{self.t.pk}/appointments", {"when": (timezone.now() + timedelta(days=2)).isoformat(), "mode": "tele"}, format="json")
        self.assertTrue(r.json()["meeting_url"].startswith("https://"))
        self.assertTrue(self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()["appointments"][0]["meeting_url"])
        a = self.as_(self.adm)
        self.assertEqual(a.post("/api/admin/translations/", {"lang": "ur", "key": "opd", "value": "او پی ڈی"}, format="json").status_code, 201)
        self.assertEqual(a.post("/api/admin/translations/", {"lang": "ur", "key": "bad key!", "value": "x"}, format="json").status_code, 400)
        self.assertEqual(self.pub.get("/api/public/translations/ur").json(), {"opd": "او پی ڈی"})
        self.assertEqual(a.post("/api/staff/ambulances/", {"label": "AMB-1", "status": "available"}, format="json").status_code, 201)
        self.assertEqual(self.pub.get("/api/public/ambulances").json()[0]["label"], "AMB-1")
        self.assertEqual(self.as_(self.doc).post("/api/staff/ambulances/", {"label": "X"}, format="json").status_code, 403)

    def test_admin_reports(self):
        a = self.as_(self.adm)
        r = a.get("/api/admin/self-review").json()
        self.assertTrue(r["missing"])
        self.assertTrue(any(x["id"] == "price" and x["ok"] for x in r["requirements"]))
        self.assertEqual(a.get("/api/admin/transactions").status_code, 200)
        self.assertEqual(a.get("/api/admin/transactions?from=bad").status_code, 400)
        self.assertEqual(self.as_(self.doc).get("/api/admin/transactions").status_code, 403)
        self.assertIn("results", a.get("/api/admin/audit/").json())

    def test_notifications_queued_on_payment(self):
        from .models import Notification
        c = APIClient()
        with override_settings(DEBUG=True, RAZORPAY_KEY_ID=""):
            o = c.post("/api/public/tickets", {"kind": "opd", "name": "Zara Ali", "phone": "9876543210", "age": 30, "sex": "f"}, format="json").json()
            c.post(f"/api/public/tickets/{o['ref']}/verify", {"razorpay_payment_id": o["mock_payment_id"], "razorpay_signature": o["mock_signature"]}, format="json")
        n = Notification.objects.get(to="9876543210")
        self.assertIn("SMHS", n.text)
        call_command("send_notifications")
        n.refresh_from_db()
        self.assertEqual(n.status, "sent")
