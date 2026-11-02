import heapq
from datetime import timedelta
import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import role_required

from . import notify, payments, pdf, services
from .models import Appointment, LabItem, LabOrder, LabTest, Location, Payment, Ticket
from .ward import Doctor, WardView, bad

LabStaff = role_required("lab", "admin")
Counter = role_required("reception", "cashier", "admin")


def loc(l):
    return {"name_en": l.name_en, "name_ur": l.name_ur, "name_ks": l.name_ks} if l else None


def eta(i):
    if i.status == "resulted":
        return None, 0
    now = timezone.now()
    if i.status == "collected":
        ready = i.collected_at + timedelta(minutes=i.test.turnaround_minutes)
    else:
        ahead = LabItem.objects.filter(test=i.test, status="ordered", order__paid_at__isnull=False, pk__lt=i.pk).count()
        ready = now + timedelta(minutes=i.test.turnaround_minutes + ahead * i.test.per_sample_minutes)
    ready = max(ready, now)
    return ready, int((ready - now).total_seconds() // 60)


def step(order, i):
    if not order.paid_at:
        return "pay", i.test.pay_at
    if i.status == "ordered":
        return "sample", i.test.sample_at
    if i.status == "collected":
        return "wait", i.test.report_at
    return ("done" if order.handed_at else "collect_report"), i.test.report_at


def item_out(order, i, results=True):
    ready, mins = eta(i)
    s, where = step(order, i)
    t = i.test
    out = {"id": i.pk, "test": {"code": t.code, "name_en": t.name_en, "name_ur": t.name_ur, "name_ks": t.name_ks}, "price": str(i.price),
           "status": i.status, "step": s, "go_to": loc(where), "ready_at": ready, "minutes_left": mins}
    if results and i.status == "resulted":
        out.update(value=None if i.value is None else float(i.value), text=i.text, unit=t.unit, ref=pdf.ref_range(t), flag=pdf.flag(i))
    return out


def order_out(o, results=True):
    return {"id": o.pk, "ref": o.ref.hex, "total": str(o.total), "paid": bool(o.paid_at), "handed": bool(o.handed_at), "created": o.created,
            "pdf_ready": any(i.status == "resulted" for i in o.items.all()),
            "items": [item_out(o, i, results) for i in o.items.select_related("test", "test__pay_at", "test__sample_at", "test__report_at").order_by("id")]}


def pdf_response(order, doctor_view=False):
    if not order.items.filter(status="resulted").exists():
        return Response({"detail": "not_ready"}, status=409)
    r = HttpResponse(pdf.build(order, doctor_view), content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="report-{order.ref.hex[:8]}.pdf"'
    r["Cache-Control"] = "no-store"
    return r


class Catalog(APIView):
    permission_classes = [role_required("doctor", "nurse", "admin")]

    def get(self, request):
        return Response(list(LabTest.objects.filter(is_active=True).order_by("id").values("code", "name_en", "name_ur", "name_ks", "price")))


class OrderTests(WardView):
    permission_classes = [Doctor]

    def post(self, request, pk):
        t = get_object_or_404(self.tickets(), pk=pk)
        codes = request.data.get("tests")
        if not isinstance(codes, list) or not 1 <= len(codes) <= 10 or not all(isinstance(c, str) for c in codes):
            return bad()
        tests = list(LabTest.objects.filter(code__in=set(codes), is_active=True))
        if len(tests) != len(set(codes)):
            return bad()
        with transaction.atomic():
            o = LabOrder.objects.create(ticket=t, ordered_by=request.user, total=sum(x.price for x in tests))
            LabItem.objects.bulk_create([LabItem(order=o, test=x, price=x.price) for x in tests])
            if not o.total:
                o.paid_at = timezone.now()
                o.save(update_fields=["paid_at"])
        return Response(order_out(o), status=201)


class PatientLab(WardView):
    def get(self, request, pk):
        t = get_object_or_404(self.tickets(), pk=pk)
        return Response([order_out(o) for o in t.lab_orders.order_by("-id")])


class StaffPdf(WardView):
    permission_classes = [Doctor]

    def get(self, request, pk):
        o = get_object_or_404(LabOrder.objects.filter(ticket__in=self.tickets()), pk=pk)
        return pdf_response(o, True)


class Appoint(WardView):
    permission_classes = [Doctor]

    def post(self, request, pk):
        from django.utils.dateparse import parse_datetime

        t = get_object_or_404(self.tickets(), pk=pk)
        when = parse_datetime(str(request.data.get("when", "")))
        if when and timezone.is_naive(when):
            when = timezone.make_aware(when)
        if not when or when <= timezone.now():
            return bad()
        tele = request.data.get("mode") == "tele"
        url = f"{settings.TELE_BASE_URL.rstrip('/')}/SMHS-{secrets.token_hex(8)}" if tele else ""
        a = Appointment.objects.create(ticket=t, doctor=request.user, department=self.dept, scheduled_at=when, note=str(request.data.get("note", ""))[:200],
                                       mode="tele" if tele else "in_person", meeting_url=url)
        notify.queue(t.phone, notify.text(t.language, "appt", when=timezone.localtime(when).strftime("%d %b %H:%M")))
        return Response({"id": a.pk, "scheduled_at": a.scheduled_at, "meeting_url": url}, status=201)


class PublicLab(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []


class PortalView(PublicLab):
    def get(self, request, ref):
        from .serializers import summary

        t = get_object_or_404(Ticket.objects.select_related("patient", "department"), ref=ref)
        pays = [{"kind": "lab" if p.lab_order_id else "ticket", "amount": str(p.amount), "method": p.method, "at": p.created}
                for p in t.payment_set.filter(status="paid").order_by("id")]
        return Response({"ticket": summary(t), "lab": [order_out(o) for o in t.lab_orders.order_by("-id")], "payments": pays,
                         "golden": ({"status": g.status, "last4": g.last4, "claim_status": g.claim_status} if (g := getattr(t, "golden", None)) else None),
                         "feedback": hasattr(t, "feedback"),
                         "appointments": [{"at": a.scheduled_at, "note": a.note, "mode": a.mode, "meeting_url": a.meeting_url, "department": a.department.name_en,
                                           "name_ur": a.department.name_ur, "name_ks": a.department.name_ks}
                                          for a in t.appointments.filter(scheduled_at__gte=timezone.now() - timedelta(days=1)).order_by("scheduled_at")]})


class LabPay(PublicLab):
    throttle_scope = "ticket"

    def post(self, request, oref):
        o = get_object_or_404(LabOrder, ref=oref)
        if o.paid_at:
            return bad()
        try:
            od = payments.create_order(o.ref.hex, o.total)
        except payments.PaymentUnavailable:
            return Response({"detail": "payment_unavailable"}, status=503)
        Payment.objects.create(ticket=o.ticket, lab_order=o, method="online", provider_order_id=od["order_id"], amount=o.total)
        out = {"order_id": od["order_id"], "amount": int(o.total * 100), "key_id": payments.settings.RAZORPAY_KEY_ID, "mock": od["mock"]}
        if od["mock"]:
            pid = "mockpay_" + o.ref.hex[:12] + str(Payment.objects.count())
            out.update(mock_payment_id=pid, mock_signature=payments.sign(od["order_id"], pid))
        return Response(out, status=201)


class LabVerify(PublicLab):
    throttle_scope = "ticket"

    def post(self, request, oref):
        o = get_object_or_404(LabOrder, ref=oref)
        oid = str(request.data.get("razorpay_order_id", ""))[:64]
        pid, sig = str(request.data.get("razorpay_payment_id", ""))[:64], str(request.data.get("razorpay_signature", ""))
        p = o.payment_set.filter(method="online", provider_order_id=oid).first()
        if not p or not pid or not payments.valid(p.provider_order_id, pid, sig) or Payment.objects.filter(provider_payment_id=pid).exists() and not o.paid_at:
            return bad()
        return Response(order_out(services.finalize_lab(o.pk, p.pk, pid)))


class PublicPdf(PublicLab):
    def get(self, request, oref):
        return pdf_response(get_object_or_404(LabOrder.objects.select_related("ticket__patient", "ticket__department"), ref=oref))


class CashLab(APIView):
    permission_classes = [Counter]

    def get(self, request):
        qs = LabOrder.objects.filter(paid_at__isnull=True).select_related("ticket__patient").order_by("id")[:100]
        return Response([{"id": o.pk, "patient_uid": o.ticket.patient.uid, "name": o.ticket.name, "total": str(o.total), "created": o.created} for o in qs])

    def post(self, request, pk):
        with transaction.atomic():
            o = get_object_or_404(LabOrder.objects.select_for_update(), pk=pk, paid_at__isnull=True)
            p = Payment.objects.create(ticket=o.ticket, lab_order=o, method="cash", amount=o.total, received_by=request.user)
            services.finalize_lab(o.pk, p.pk)
        return Response({"ok": True})


class LabQueue(APIView):
    permission_classes = [LabStaff]

    def get(self, request):
        qs = (LabItem.objects.filter(order__paid_at__isnull=False, status__in=["ordered", "collected"])
              .select_related("test", "order__ticket__patient"))
        h = [(i.order.ticket.priority or 9, i.order.paid_at, i.pk, i) for i in qs]
        heapq.heapify(h)
        out = []
        while h:
            i = heapq.heappop(h)[3]
            t = i.order.ticket
            out.append({"id": i.pk, "order_id": i.order_id, "patient_uid": t.patient.uid, "name": t.name, "emergency": t.kind == "emergency",
                        "priority": t.priority, "status": i.status, "unit": i.test.unit, "ref": pdf.ref_range(i.test),
                        "test": {"code": i.test.code, "name_en": i.test.name_en, "name_ur": i.test.name_ur, "name_ks": i.test.name_ks}})
        return Response(out)


class Collect(APIView):
    permission_classes = [LabStaff]

    def post(self, request, pk):
        with transaction.atomic():
            i = get_object_or_404(LabItem.objects.select_for_update(), pk=pk, status="ordered", order__paid_at__isnull=False)
            i.status, i.collected_at = "collected", timezone.now()
            i.save(update_fields=["status", "collected_at"])
        return Response({"status": "collected"})


class Result(APIView):
    permission_classes = [LabStaff]

    def post(self, request, pk):
        v, txt = request.data.get("value"), str(request.data.get("text", "")).strip()[:200]
        val = None
        if v not in (None, ""):
            try:
                val = Decimal(str(v))
                if not val.is_finite() or abs(val) >= Decimal("1e8"):
                    raise InvalidOperation
            except InvalidOperation:
                return bad()
        if val is None and not txt:
            return bad()
        with transaction.atomic():
            i = get_object_or_404(LabItem.objects.select_for_update(), pk=pk, status="collected")
            i.value, i.text, i.note = val, txt, str(request.data.get("note", ""))[:200]
            i.status, i.resulted_at, i.resulted_by = "resulted", timezone.now(), request.user
            i.save()
            o = i.order
            if not o.items.exclude(status="resulted").exists():
                notify.queue(o.ticket.phone, notify.text(o.ticket.language, "report"))
        return Response({"status": "resulted", "flag": pdf.flag(i)})


class Handover(APIView):
    permission_classes = [LabStaff]

    def post(self, request, pk):
        o = get_object_or_404(LabOrder, pk=pk, handed_at__isnull=True)
        if not o.items.filter(status="resulted").exists():
            return bad()
        o.handed_at = timezone.now()
        o.save(update_fields=["handed_at"])
        return Response({"ok": True})


class Ready(APIView):
    permission_classes = [LabStaff]

    def get(self, request):
        qs = (LabOrder.objects.filter(handed_at__isnull=True, items__status="resulted").distinct()
              .select_related("ticket__patient").order_by("id")[:100])
        return Response([{"id": o.pk, "patient_uid": o.ticket.patient.uid, "name": o.ticket.name,
                          "pending": o.items.exclude(status="resulted").count()} for o in qs])
