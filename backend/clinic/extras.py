import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.crypto import decrypt, encrypt
from accounts.permissions import role_required

from . import notify, review
from .models import Admission, Ambulance, Bed, Department, Feedback, GoldenCard, Patient, PatientOTP, Payment, Ticket, TextOverride
from .serializers import DeptOut
from .ward import WardView, bad

IsAdmin = role_required("admin")


class Public(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []


class GoldenSubmit(Public):
    throttle_scope = "ticket"

    def post(self, request, ref):
        t = get_object_or_404(Ticket, ref=ref)
        if t.status != "paid" or not t.department_id:
            return Response({"detail": "not_ready"}, status=409)
        no = re.sub(r"[\s-]", "", str(request.data.get("card_no", ""))).upper()
        if not re.fullmatch(r"[A-Z0-9]{8,20}", no):
            return bad()
        g = GoldenCard.objects.filter(ticket=t).first()
        if g and g.status != "rejected":
            return bad()
        GoldenCard.objects.update_or_create(ticket=t, defaults=dict(
            department=t.department, number_enc=encrypt(no), last4=no[-4:], holder=str(request.data.get("holder", "")).strip()[:80],
            status="pending", claim_status="none", note="", decided_by=None, decided_at=None))
        return Response({"status": "pending"}, status=201)


class GoldenList(WardView):
    def get(self, request):
        qs = GoldenCard.objects.filter(department=self.dept, status=request.query_params.get("status", "pending")).select_related("ticket__patient").order_by("id")[:100]
        return Response([{"id": g.pk, "patient_uid": g.ticket.patient.uid, "name": g.ticket.name, "holder": g.holder, "number": decrypt(g.number_enc),
                          "status": g.status, "claim_status": g.claim_status, "created": g.created} for g in qs])


class GoldenDecide(WardView):
    def post(self, request, pk):
        g = get_object_or_404(GoldenCard.objects.select_related("ticket"), pk=pk, department=self.dept, status="pending")
        act = request.data.get("action")
        if act not in ("verify", "reject"):
            return bad()
        g.status, g.note, g.decided_by, g.decided_at = ("verified" if act == "verify" else "rejected"), str(request.data.get("note", ""))[:200], request.user, timezone.now()
        g.save()
        notify.queue(g.ticket.phone, notify.text(g.ticket.language, "golden", status="verified" if act == "verify" else "not accepted"))
        return Response({"status": g.status})


class GoldenClaim(WardView):
    def post(self, request, pk):
        g = get_object_or_404(GoldenCard, pk=pk, department=self.dept, status="verified")
        cs = request.data.get("claim_status")
        if cs not in ("submitted", "approved", "rejected"):
            return bad()
        g.claim_status = cs
        g.save(update_fields=["claim_status"])
        return Response({"claim_status": cs})


class FreeBeds(WardView):
    def get(self, request):
        used = Admission.objects.filter(status="admitted", bed__isnull=False).values_list("bed_id", flat=True)
        return Response(list(Bed.objects.filter(department=self.dept, is_active=True).exclude(pk__in=used).order_by("label").values("id", "label")))


class OtpRequest(Public):
    throttle_scope = "otp"

    def post(self, request):
        uid, phone = str(request.data.get("uid", ""))[:16], str(request.data.get("phone", ""))[:10]
        p = Patient.objects.filter(uid=uid, phone=phone).first()
        if p and PatientOTP.objects.filter(patient=p, created__gte=timezone.now() - timedelta(hours=1)).count() < 5:
            PatientOTP.objects.filter(patient=p, used=False).update(used=True)
            code = f"{secrets.randbelow(10 ** 6):06d}"
            PatientOTP.objects.create(patient=p, code_hash=self.h(code, p.pk), expires=timezone.now() + timedelta(minutes=5))
            notify.queue(p.phone, notify.text(p.language, "otp", code=code), secret=True, now=True)
        return Response({"sent": True})

    @staticmethod
    def h(code, pk):
        return hmac.new(settings.SECRET_KEY.encode(), f"{code}:{pk}".encode(), hashlib.sha256).hexdigest()


class OtpVerify(Public):
    throttle_scope = "otp"

    def post(self, request):
        uid, phone, code = str(request.data.get("uid", ""))[:16], str(request.data.get("phone", ""))[:10], str(request.data.get("code", ""))[:6]
        p = Patient.objects.filter(uid=uid, phone=phone).first()
        o = p and PatientOTP.objects.filter(patient=p, used=False, expires__gt=timezone.now()).order_by("-id").first()
        if not o or o.attempts >= 5:
            return Response({"detail": "invalid"}, status=401)
        if not hmac.compare_digest(o.code_hash, OtpRequest.h(code, p.pk)):
            o.attempts += 1
            o.save(update_fields=["attempts"])
            return Response({"detail": "invalid"}, status=401)
        o.used = True
        o.save(update_fields=["used"])
        return Response({"token": signing.dumps({"p": p.pk}, salt="patient")})


class History(Public):
    def get(self, request):
        try:
            pid = signing.loads(request.headers.get("X-Patient-Token", ""), salt="patient", max_age=3600)["p"]
        except (signing.BadSignature, KeyError):
            return Response({"detail": "invalid"}, status=401)
        ts = Ticket.objects.filter(patient_id=pid, status="paid").select_related("department").order_by("-id")[:50]
        return Response([{"ref": t.ref.hex, "date": t.created, "kind": t.kind, "state": t.state,
                          "department": DeptOut(t.department).data if t.department else None} for t in ts])


class FeedbackSubmit(Public):
    throttle_scope = "ticket"

    def post(self, request, ref):
        t = get_object_or_404(Ticket, ref=ref)
        r = request.data.get("rating")
        if not t.triaged_at or not isinstance(r, int) or isinstance(r, bool) or not 1 <= r <= 5 or Feedback.objects.filter(ticket=t).exists():
            return bad()
        Feedback.objects.create(ticket=t, rating=r, comment=str(request.data.get("comment", ""))[:300])
        return Response({"ok": True}, status=201)


class BedsPublic(Public):
    def get(self, request):
        tot = dict(Bed.objects.filter(is_active=True).values_list("department").annotate(n=Count("id")))
        occ = dict(Admission.objects.filter(status="admitted", bed__isnull=False).values_list("bed__department").annotate(n=Count("id")))
        return Response([{**DeptOut(d).data, "total": tot[d.pk], "free": max(tot[d.pk] - occ.get(d.pk, 0), 0)} for d in Department.objects.filter(pk__in=tot).order_by("id")])


class AmbulancesPublic(Public):
    def get(self, request):
        return Response(list(Ambulance.objects.order_by("label").values("label", "status", "updated")))


class Translations(Public):
    def get(self, request, lang):
        if lang not in ("en", "ur", "ks"):
            return Response(status=404)
        r = Response(dict(TextOverride.objects.filter(lang=lang).values_list("key", "value")))
        r["Cache-Control"] = "public, max-age=60"
        return r


class Transactions(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from datetime import date

        qs = Payment.objects.filter(status="paid")
        try:
            if request.query_params.get("from"):
                qs = qs.filter(created__date__gte=date.fromisoformat(request.query_params["from"]))
            if request.query_params.get("to"):
                qs = qs.filter(created__date__lte=date.fromisoformat(request.query_params["to"]))
        except ValueError:
            return bad()
        if request.query_params.get("method") in ("online", "cash"):
            qs = qs.filter(method=request.query_params["method"])
        tot = []
        for m in ("online", "cash"):
            for lab in (False, True):
                a = qs.filter(method=m, lab_order__isnull=not lab).aggregate(n=Count("id"), total=Sum("amount"))
                if a["n"]:
                    tot.append({"method": m, "kind": "lab" if lab else "ticket", "count": a["n"], "sum": str(a["total"])})
        fb = Feedback.objects.aggregate(avg=Avg("rating"), n=Count("id"))
        return Response({
            "totals": tot,
            "feedback": {"average": round(fb["avg"], 2) if fb["avg"] else None, "count": fb["n"]},
            "rows": [{"id": p.pk, "at": p.created, "patient_uid": p.ticket.patient.uid, "method": p.method, "kind": "lab" if p.lab_order_id else "ticket",
                      "amount": str(p.amount), "ref": p.provider_payment_id or "", "by": p.received_by.username if p.received_by else ""}
                     for p in qs.select_related("ticket__patient", "received_by").order_by("-id")[:200]]})


class SelfReview(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        items = [{"id": i, "text": t, "ok": bool(ok), "detail": d} for i, t, ok, d in review.checks()]
        return Response({"requirements": items, "missing": [x["text"] for x in items if not x["ok"]],
                         "recommendations": [{"name": n, "status": s, "note": t} for n, s, t in review.RECOMMENDATIONS]})
