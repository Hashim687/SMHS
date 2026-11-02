import json

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import role_required
from smhs.pagination import Pg

from . import payments, services, triage
from .models import Ambulance, Bed, Department, Feedback, LabTest, Notification, TextOverride, Location, Payment, StaffAssignment, Symptom, Ticket, TicketPrice, TriageRule
from .serializers import DeptOut, TicketCreate, summary

IsAdmin = role_required("admin")
Cashiers = role_required("reception", "cashier", "admin")
QueueViewers = role_required("doctor", "nurse", "admin", "reception")


class Public(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []


class Departments(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = DeptOut
    queryset = Department.objects.filter(is_active=True).order_by("id")


class Symptoms(Public):
    def get(self, request):
        return Response(list(Symptom.objects.filter(is_active=True).order_by("id").values("key", "icon")))


class Prices(Public):
    def get(self, request):
        return Response({p.kind: str(p.amount) for p in TicketPrice.objects.all()})


class TicketCreateView(Public):
    throttle_scope = "ticket"

    def post(self, request):
        s = TicketCreate(data=request.data)
        s.is_valid(raise_exception=True)
        price = get_object_or_404(TicketPrice, kind=s.validated_data["kind"])
        t = Ticket.objects.create(**s.validated_data, amount=price.amount)
        try:
            o = payments.create_order(t.ref.hex, t.amount)
        except payments.PaymentUnavailable:
            t.delete()
            return Response({"detail": "payment_unavailable"}, status=503)
        Payment.objects.create(ticket=t, method="online", provider_order_id=o["order_id"], amount=t.amount)
        out = {"ref": t.ref.hex, "order_id": o["order_id"], "amount": int(t.amount * 100),
               "key_id": payments.settings.RAZORPAY_KEY_ID, "mock": o["mock"]}
        if o["mock"]:
            pid = "mockpay_" + t.ref.hex[:12]
            out.update(mock_payment_id=pid, mock_signature=payments.sign(o["order_id"], pid))
        return Response(out, status=201)


class TicketVerify(Public):
    throttle_scope = "ticket"

    def post(self, request, ref):
        t = get_object_or_404(Ticket, ref=ref)
        p = t.payment_set.filter(method="online").order_by("-id").first()
        pid, sig = str(request.data.get("razorpay_payment_id", ""))[:64], str(request.data.get("razorpay_signature", ""))
        if not p or not pid or not payments.valid(p.provider_order_id, pid, sig):
            return Response({"detail": "invalid"}, status=400)
        if t.status != "paid" and Payment.objects.filter(provider_payment_id=pid).exists():
            return Response({"detail": "invalid"}, status=400)
        return Response(summary(services.finalize(t.pk, p.pk, pid)))


class TicketStatus(Public):
    def get(self, request, ref):
        return Response(summary(get_object_or_404(Ticket, ref=ref)))


class TicketSymptoms(Public):
    throttle_scope = "symptoms"

    def post(self, request, ref):
        t = get_object_or_404(Ticket.objects.select_related("patient", "department"), ref=ref)
        if t.status != "paid":
            return Response({"detail": "unpaid"}, status=402)
        if t.triaged_at:
            return Response(summary(t))
        keys = request.data.get("symptoms")
        if not isinstance(keys, list) or not 1 <= len(keys) <= 12 or not all(isinstance(k, str) for k in keys):
            return Response({"detail": "invalid"}, status=400)
        try:
            r = triage.run(t.kind, keys, t.age)
            t = services.assign(t, r, keys)
        except (ValueError, Department.DoesNotExist):
            return Response({"detail": "invalid"}, status=400)
        return Response(summary(t))


class Webhook(Public):
    def post(self, request):
        if not payments.valid_webhook(request.body, request.headers.get("X-Razorpay-Signature", "")):
            return Response(status=400)
        try:
            d = json.loads(request.body)
            e = d["payload"]["payment"]["entity"]
        except (ValueError, KeyError, TypeError):
            return Response(status=400)
        if d.get("event") == "payment.captured":
            p = Payment.objects.filter(provider_order_id=e.get("order_id"), method="online").first()
            if p and not Payment.objects.filter(provider_payment_id=e["id"]).exists():
                (services.finalize_lab(p.lab_order_id, p.pk, e["id"]) if p.lab_order_id else services.finalize(p.ticket_id, p.pk, e["id"]))
        return Response({"ok": True})


class CashTicket(APIView):
    permission_classes = [Cashiers]

    def post(self, request):
        s = TicketCreate(data=request.data)
        s.is_valid(raise_exception=True)
        price = get_object_or_404(TicketPrice, kind=s.validated_data["kind"])
        with transaction.atomic():
            t = Ticket.objects.create(**s.validated_data, amount=price.amount)
            p = Payment.objects.create(ticket=t, method="cash", amount=t.amount, received_by=request.user)
            t = services.finalize(t.pk, p.pk)
        return Response({"ref": t.ref.hex, **summary(t)}, status=201)


class EmergencyQueue(APIView):
    permission_classes = [QueueViewers]

    def get(self, request):
        from django.utils import timezone

        qs = Ticket.objects.filter(kind="emergency", triaged_at__date=timezone.localdate()).select_related("patient", "department")
        return Response([{"patient_uid": t.patient.uid, "name": t.name, "age": t.age, "category": t.category,
                          "priority": t.priority, "department": t.department.code, "token_no": t.token_no,
                          "triaged_at": t.triaged_at} for t in triage.ordered(qs)])


def admin_vs(m, f, perm=None, ro=False, paged=False):
    class S(serializers.ModelSerializer):
        class Meta:
            model = m
            fields = f

    class V(viewsets.ReadOnlyModelViewSet if ro else viewsets.ModelViewSet):
        permission_classes = [perm or IsAdmin]
        serializer_class = S
        queryset = m.objects.order_by("-pk" if paged else "pk")
        pagination_class = Pg if paged else None

    return V


DepartmentAdmin = admin_vs(Department, ["id", "code", "name_en", "name_ur", "name_ks", "head", "emergency_category", "is_active"])
PriceAdmin = admin_vs(TicketPrice, ["kind", "amount"])
SymptomAdmin = admin_vs(Symptom, ["id", "key", "icon", "emergency_category", "severity", "is_active"])
RuleAdmin = admin_vs(TriageRule, ["id", "symptom", "department", "weight"])
AssignmentAdmin = admin_vs(StaffAssignment, ["id", "user", "department"])
LocationAdmin = admin_vs(Location, ["id", "code", "name_en", "name_ur", "name_ks"])
LabTestAdmin = admin_vs(LabTest, ["id", "code", "name_en", "name_ur", "name_ks", "price", "unit", "ref_low", "ref_high", "turnaround_minutes",
                                  "per_sample_minutes", "pay_at", "sample_at", "report_at", "is_active"])
BedAdmin = admin_vs(Bed, ["id", "department", "label", "is_active"])
AmbulanceAdmin = admin_vs(Ambulance, ["id", "label", "status", "note", "updated"], perm=Cashiers)
TextAdmin = admin_vs(TextOverride, ["id", "lang", "key", "value"])
FeedbackAdmin = admin_vs(Feedback, ["id", "ticket", "rating", "comment", "created"], ro=True, paged=True)
NotificationAdmin = admin_vs(Notification, ["id", "to", "channel", "status", "attempts", "created", "sent_at"], ro=True, paged=True)
