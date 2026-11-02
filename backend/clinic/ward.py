from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import role_required

from . import notify
from .models import Admission, Bed, StatusUpdate, Ticket
from .serializers import DeptOut

Doctor = role_required("doctor")
Floor = role_required("doctor", "nurse")
ROLE_STATES = {"nurse": {"waiting", "vitals", "observation"}, "doctor": {"vitals", "in_consult", "observation", "done"}}
bad = lambda: Response({"detail": "invalid"}, status=400)


def dept_of(u):
    a = getattr(u, "assignment", None)
    return a.department if a else None


def adm_out(a):
    return {"id": a.pk, "status": a.status, "ward": a.ward, "reason": a.reason, "created": a.created}


def row(t):
    a = next(iter(t.admissions.all()), None)
    return {"id": t.pk, "patient_uid": t.patient.uid, "name": t.name, "age": t.age, "sex": t.sex, "kind": t.kind,
            "symptoms": t.symptoms, "category": t.category, "priority": t.priority, "token_no": t.token_no,
            "state": t.state, "nurse": t.nurse.username if t.nurse else None, "triaged_at": t.triaged_at,
            "admission": adm_out(a) if a else None}


class Profile(APIView):
    def get(self, request):
        d = dept_of(request.user)
        return Response({"role": request.user.role, "department": DeptOut(d).data if d else None,
                         "is_head": bool(d and d.head_id == request.user.pk)})


class WardView(APIView):
    permission_classes = [Floor]

    def initial(self, request, *a, **k):
        super().initial(request, *a, **k)
        self.dept = dept_of(request.user)
        if not self.dept:
            raise PermissionDenied("no_department")

    def tickets(self):
        return (Ticket.objects.filter(department=self.dept, triaged_at__isnull=False)
                .select_related("patient", "nurse")
                .prefetch_related(Prefetch("admissions", queryset=Admission.objects.order_by("-id"))))

    def is_head(self):
        return self.dept.head_id == self.request.user.pk


class Patients(WardView):
    def get(self, request):
        try:
            day = date.fromisoformat(request.query_params.get("date") or str(timezone.localdate()))
        except ValueError:
            return bad()
        qs = self.tickets().filter(triaged_at__date=day)
        if request.query_params.get("mine") == "1":
            qs = qs.filter(nurse=request.user)
        return Response([row(t) for t in sorted(qs, key=lambda t: (t.priority or 9, t.triaged_at))])


class History(WardView):
    permission_classes = [Doctor]

    def get(self, request, uid):
        qs = self.tickets().filter(patient__uid=uid).order_by("-triaged_at")[:50]
        return Response([{"date": t.triaged_at, "symptoms": t.symptoms, "category": t.category,
                          "priority": t.priority, "state": t.state} for t in qs])


class SetStatus(WardView):
    def post(self, request, pk):
        t = get_object_or_404(self.tickets(), pk=pk)
        st = request.data.get("status")
        if st not in ROLE_STATES[request.user.role] or t.state == "admitted":
            return bad()
        t.state = st
        t.save(update_fields=["state"])
        StatusUpdate.objects.create(ticket=t, by=request.user, status=st, note=str(request.data.get("note", ""))[:200])
        return Response({"state": st})


class Claim(WardView):
    permission_classes = [role_required("nurse")]

    def post(self, request, pk):
        t = get_object_or_404(self.tickets(), pk=pk)
        t.nurse = request.user
        t.save(update_fields=["nurse"])
        return Response({"nurse": request.user.username})


class AdmitRequest(WardView):
    permission_classes = [Doctor]

    def post(self, request, pk):
        t = get_object_or_404(self.tickets(), pk=pk)
        reason = str(request.data.get("reason", "")).strip()
        if not 3 <= len(reason) <= 200:
            return bad()
        try:
            with transaction.atomic():
                a = Admission.objects.create(ticket=t, department=self.dept, requested_by=request.user, reason=reason)
        except IntegrityError:
            return bad()
        return Response(adm_out(a), status=201)


class Admissions(WardView):
    def get(self, request):
        qs = Admission.objects.filter(department=self.dept).select_related("ticket__patient", "requested_by").order_by("-id")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return Response([{**adm_out(a), "ticket_id": a.ticket_id, "requested_by": a.requested_by.username,
                          "patient": {"uid": a.ticket.patient.uid, "name": a.ticket.name, "age": a.ticket.age, "sex": a.ticket.sex}}
                         for a in qs[:100]])


class Decide(WardView):
    permission_classes = [Doctor]

    def post(self, request, pk):
        if not self.is_head():
            raise PermissionDenied("not_head")
        act, ward, bed_id = request.data.get("action"), str(request.data.get("ward", "")).strip()[:40], request.data.get("bed")
        if act not in ("admit", "reject") or (act == "admit" and not ward and not bed_id):
            return bad()
        with transaction.atomic():
            a = get_object_or_404(Admission.objects.select_for_update(), pk=pk, department=self.dept, status="requested")
            if act == "admit" and bed_id:
                try:
                    bed = Bed.objects.select_for_update().get(pk=int(bed_id), department=self.dept, is_active=True)
                except (Bed.DoesNotExist, ValueError, TypeError):
                    return bad()
                if Admission.objects.filter(bed=bed, status="admitted").exists():
                    return bad()
                a.bed, ward = bed, bed.label
            a.status, a.ward, a.decided_by, a.decided_at = ("admitted" if act == "admit" else "rejected"), ward, request.user, timezone.now()
            a.save()
            if act == "admit":
                a.ticket.state = "admitted"
                a.ticket.save(update_fields=["state"])
                StatusUpdate.objects.create(ticket=a.ticket, by=request.user, status="admitted", note=ward)
            notify.queue(a.ticket.phone, notify.text(a.ticket.language, "admit", ward=ward) if act == "admit" else notify.text(a.ticket.language, "reject"))
        return Response(adm_out(a))


class Discharge(WardView):
    permission_classes = [Doctor]

    def post(self, request, pk):
        with transaction.atomic():
            a = get_object_or_404(Admission.objects.select_for_update(), pk=pk, department=self.dept, status="admitted")
            if not self.is_head() and a.requested_by_id != request.user.pk:
                raise PermissionDenied("forbidden")
            a.status, a.discharged_at = "discharged", timezone.now()
            a.save()
            a.ticket.state = "done"
            a.ticket.save(update_fields=["state"])
            StatusUpdate.objects.create(ticket=a.ticket, by=request.user, status="discharged")
        return Response(adm_out(a))
