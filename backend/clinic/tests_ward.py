from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User

from .models import Department, Patient, StaffAssignment, Ticket

PW = "Str0ng-Pass-123"


def mk(dept, name, phone, priority=None, kind="opd"):
    p = Patient.objects.create(name=name, phone=phone, age=30, sex="m")
    p.uid = f"T{p.pk}"
    p.save()
    return Ticket.objects.create(kind=kind, name=name, phone=phone, age=30, sex="m", amount=10, status="paid", patient=p,
                                 department=Department.objects.get(code=dept), symptoms=["chest_pain"], priority=priority,
                                 token_no=1, triaged_at=timezone.now(), paid_at=timezone.now(), state="waiting")


class Ward(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed")
        cardio, neuro = (Department.objects.get(code=c) for c in ("CARDIO", "NEURO"))
        self.head = User.objects.create_user("head", password=PW, role="doctor")
        self.doc = User.objects.create_user("doc", password=PW, role="doctor")
        self.nur = User.objects.create_user("nur", password=PW, role="nurse")
        self.nd = User.objects.create_user("nd", password=PW, role="doctor")
        self.free = User.objects.create_user("free", password=PW, role="doctor")
        for u, d in ((self.head, cardio), (self.doc, cardio), (self.nur, cardio), (self.nd, neuro)):
            StaffAssignment.objects.create(user=u, department=d)
        cardio.head = self.head
        cardio.save()
        self.a = mk("CARDIO", "Amir", "9000000001")
        self.e = mk("CARDIO", "Eman", "9000000002", priority=1, kind="emergency")
        self.n = mk("NEURO", "Nabi", "9000000003")

    def as_(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_domain_scope_and_order(self):
        r = self.as_(self.doc).get("/api/staff/patients").json()
        self.assertEqual([x["name"] for x in r], ["Eman", "Amir"])
        self.assertEqual(self.as_(self.nd).get("/api/staff/patients").json()[0]["name"], "Nabi")
        self.assertEqual(self.as_(self.free).get("/api/staff/patients").status_code, 403)

    def test_cross_department_blocked(self):
        c = self.as_(self.doc)
        self.assertEqual(c.post(f"/api/staff/patients/{self.n.pk}/status", {"status": "vitals"}, format="json").status_code, 404)
        self.assertEqual(c.post(f"/api/staff/patients/{self.n.pk}/admit-request", {"reason": "observation"}, format="json").status_code, 404)
        self.assertEqual(c.get(f"/api/staff/patients/history/{self.n.patient.uid}").json(), [])
        self.assertEqual(len(c.get(f"/api/staff/patients/history/{self.a.patient.uid}").json()), 1)

    def test_nurse_limits_and_claim(self):
        c = self.as_(self.nur)
        self.assertEqual(c.post(f"/api/staff/patients/{self.a.pk}/status", {"status": "in_consult"}, format="json").status_code, 400)
        self.assertEqual(c.post(f"/api/staff/patients/{self.a.pk}/status", {"status": "vitals", "note": "bp 120/80"}, format="json").status_code, 200)
        self.assertEqual(c.post(f"/api/staff/patients/{self.a.pk}/admit-request", {"reason": "observation"}, format="json").status_code, 403)
        self.assertEqual(c.post(f"/api/staff/patients/{self.a.pk}/claim").status_code, 200)
        self.assertEqual([x["name"] for x in c.get("/api/staff/patients?mine=1").json()], ["Amir"])

    def test_admission_flow(self):
        d, h = self.as_(self.doc), self.as_(self.head)
        r = d.post(f"/api/staff/patients/{self.a.pk}/admit-request", {"reason": "chest pain, ECG changes"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(d.post(f"/api/staff/patients/{self.a.pk}/admit-request", {"reason": "again please"}, format="json").status_code, 400)
        aid = r.json()["id"]
        self.assertEqual(d.post(f"/api/staff/admissions/{aid}/decide", {"action": "admit", "ward": "W1"}, format="json").status_code, 403)
        self.assertEqual(h.post(f"/api/staff/admissions/{aid}/decide", {"action": "admit"}, format="json").status_code, 400)
        self.assertEqual(self.as_(self.nd).post(f"/api/staff/admissions/{aid}/decide", {"action": "admit", "ward": "W1"}, format="json").status_code, 403)
        self.assertEqual(h.post(f"/api/staff/admissions/{aid}/decide", {"action": "admit", "ward": "W1"}, format="json").status_code, 200)
        pub = APIClient().get(f"/api/public/tickets/{self.a.ref.hex}").json()
        self.assertEqual(pub["admission"], {"status": "admitted", "ward": "W1"})
        self.assertEqual(pub["state"], "admitted")
        self.assertEqual(d.post(f"/api/staff/patients/{self.a.pk}/status", {"status": "done"}, format="json").status_code, 400)
        self.assertEqual(self.as_(self.nur).get("/api/staff/admissions").json()[0]["status"], "admitted")
        self.assertEqual(h.post(f"/api/staff/admissions/{aid}/discharge").status_code, 200)
        self.assertEqual(APIClient().get(f"/api/public/tickets/{self.a.ref.hex}").json()["state"], "done")

    def test_reject_allows_new_request(self):
        d, h = self.as_(self.doc), self.as_(self.head)
        aid = d.post(f"/api/staff/patients/{self.a.pk}/admit-request", {"reason": "observation"}, format="json").json()["id"]
        h.post(f"/api/staff/admissions/{aid}/decide", {"action": "reject"}, format="json")
        self.assertEqual(d.post(f"/api/staff/patients/{self.a.pk}/admit-request", {"reason": "second try"}, format="json").status_code, 201)
