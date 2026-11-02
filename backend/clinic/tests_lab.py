from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User

from .models import Department, LabTest, StaffAssignment
from .tests_ward import PW, mk

PDF = b"%PDF"


@override_settings(DEBUG=True, RAZORPAY_KEY_ID="")
class Lab(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed")
        cardio, neuro = Department.objects.get(code="CARDIO"), Department.objects.get(code="NEURO")
        self.doc = User.objects.create_user("doc", password=PW, role="doctor")
        self.nd = User.objects.create_user("nd", password=PW, role="doctor")
        self.nur = User.objects.create_user("nur", password=PW, role="nurse")
        self.lab = User.objects.create_user("lab", password=PW, role="lab")
        self.cash = User.objects.create_user("cash", password=PW, role="cashier")
        for u, d in ((self.doc, cardio), (self.nd, neuro), (self.nur, cardio)):
            StaffAssignment.objects.create(user=u, department=d)
        self.t = mk("CARDIO", "Amir", "9000000001")
        self.t.language = "ur"
        self.t.save()
        self.e = mk("CARDIO", "Eman", "9000000002", priority=1, kind="emergency")
        self.pub = APIClient()

    def as_(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def order(self, t=None, codes=("HB", "FBS")):
        r = self.as_(self.doc).post(f"/api/staff/patients/{(t or self.t).pk}/lab-orders", {"tests": list(codes)}, format="json")
        self.assertEqual(r.status_code, 201)
        return r.json()

    def pay_online(self, o):
        p = self.pub.post(f"/api/public/lab-orders/{o['ref']}/pay").json()
        r = self.pub.post(f"/api/public/lab-orders/{o['ref']}/verify", {"razorpay_order_id": p["order_id"], "razorpay_payment_id": p["mock_payment_id"], "razorpay_signature": p["mock_signature"]}, format="json")
        return r

    def test_order_scope_and_guidance(self):
        o = self.order()
        self.assertEqual(o["total"], "100.00")
        self.assertEqual(o["items"][0]["step"], "pay")
        self.assertIn("Cashier", o["items"][0]["go_to"]["name_en"])
        other = mk("NEURO", "Nabi", "9000000003")
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/patients/{other.pk}/lab-orders", {"tests": ["HB"]}, format="json").status_code, 404)
        self.assertEqual(self.as_(self.nur).post(f"/api/staff/patients/{self.t.pk}/lab-orders", {"tests": ["HB"]}, format="json").status_code, 403)
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/patients/{self.t.pk}/lab-orders", {"tests": ["NOPE"]}, format="json").status_code, 400)

    def test_full_flow_pdf(self):
        o = self.order()
        self.assertEqual(self.pay_online(o).status_code, 200)
        self.assertEqual(self.pub.post(f"/api/public/lab-orders/{o['ref']}/pay").status_code, 400)
        lab = self.as_(self.lab)
        q = lab.get("/api/lab/queue").json()
        self.assertEqual(len(q), 2)
        for i in q:
            self.assertEqual(lab.post(f"/api/lab/items/{i['id']}/result", {"value": 5}, format="json").status_code, 404)
            self.assertEqual(lab.post(f"/api/lab/items/{i['id']}/collect").status_code, 200)
        port = self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()
        it = port["lab"][0]["items"][0]
        self.assertEqual((it["step"], it["status"]), ("wait", "collected"))
        self.assertGreater(it["minutes_left"], 0)
        self.assertEqual(self.pub.get(f"/api/public/lab-orders/{o['ref']}/report.pdf").status_code, 409)
        ids = {i["test"]["code"]: i["id"] for i in q}
        self.assertEqual(lab.post(f"/api/lab/items/{ids['HB']}/result", {"value": "8.2"}, format="json").json()["flag"], "L")
        self.assertEqual(lab.post(f"/api/lab/items/{ids['FBS']}/result", {"value": 90}, format="json").json()["flag"], "N")
        self.assertEqual(lab.post(f"/api/lab/items/{ids['FBS']}/result", {"value": 90}, format="json").status_code, 404)
        r = self.pub.get(f"/api/public/lab-orders/{o['ref']}/report.pdf")
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "application/pdf"))
        self.assertTrue(r.content.startswith(PDF))
        d = self.as_(self.doc).get(f"/api/staff/lab-orders/{o['id']}/report.pdf")
        self.assertTrue(d.content.startswith(PDF))
        self.assertEqual(self.as_(self.nd).get(f"/api/staff/lab-orders/{o['id']}/report.pdf").status_code, 404)
        self.assertEqual(len(lab.get("/api/lab/ready").json()), 1)
        self.assertEqual(lab.post(f"/api/lab/orders/{o['id']}/handover").status_code, 200)
        self.assertEqual(lab.get("/api/lab/ready").json(), [])
        self.assertEqual(self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()["lab"][0]["items"][0]["step"], "done")

    def test_urdu_pdf_and_bad_values(self):
        o = self.order(codes=("CREAT",))
        self.pay_online(o)
        lab = self.as_(self.lab)
        i = lab.get("/api/lab/queue").json()[0]
        lab.post(f"/api/lab/items/{i['id']}/collect")
        self.assertEqual(lab.post(f"/api/lab/items/{i['id']}/result", {"value": "abc"}, format="json").status_code, 400)
        self.assertEqual(lab.post(f"/api/lab/items/{i['id']}/result", {}, format="json").status_code, 400)
        lab.post(f"/api/lab/items/{i['id']}/result", {"value": 2.4}, format="json")
        r = self.pub.get(f"/api/public/lab-orders/{o['ref']}/report.pdf")
        self.assertTrue(r.content.startswith(PDF))

    def test_forged_payment_and_cash(self):
        o = self.order()
        p = self.pub.post(f"/api/public/lab-orders/{o['ref']}/pay").json()
        r = self.pub.post(f"/api/public/lab-orders/{o['ref']}/verify", {"razorpay_order_id": p["order_id"], "razorpay_payment_id": "x", "razorpay_signature": "y"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.as_(self.doc).post(f"/api/staff/lab-orders/{o['id']}/cash").status_code, 403)
        c = self.as_(self.cash)
        self.assertEqual(c.get("/api/staff/lab-orders/unpaid").json()[0]["id"], o["id"])
        self.assertEqual(c.post(f"/api/staff/lab-orders/{o['id']}/cash").status_code, 200)
        self.assertEqual(c.post(f"/api/staff/lab-orders/{o['id']}/cash").status_code, 404)
        pays = self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()["payments"]
        self.assertEqual([(x["kind"], x["method"]) for x in pays], [("lab", "cash")])

    def test_queue_emergency_first(self):
        a, b = self.order(self.t), self.order(self.e)
        self.pay_online(a)
        self.pay_online(b)
        q = self.as_(self.lab).get("/api/lab/queue").json()
        self.assertTrue(q[0]["emergency"])
        self.assertEqual(self.as_(self.doc).get("/api/lab/queue").status_code, 403)

    def test_appointment_portal(self):
        c = self.as_(self.doc)
        when = (timezone.now() + timedelta(days=7)).isoformat()
        self.assertEqual(c.post(f"/api/staff/patients/{self.t.pk}/appointments", {"when": when, "note": "review ECG"}, format="json").status_code, 201)
        past = (timezone.now() - timedelta(days=1)).isoformat()
        self.assertEqual(c.post(f"/api/staff/patients/{self.t.pk}/appointments", {"when": past}, format="json").status_code, 400)
        self.assertEqual(len(self.pub.get(f"/api/public/tickets/{self.t.ref.hex}/portal").json()["appointments"]), 1)

    def test_price_zero_and_catalog(self):
        LabTest.objects.filter(code="HB").update(price=0)
        o = self.order(codes=("HB",))
        self.assertTrue(o["paid"])
        self.assertEqual(len(self.as_(self.doc).get("/api/staff/lab-catalog").json()), 10)
