from django.db import transaction
from django.utils import timezone

from . import notify
from .models import Department, Patient, Payment, Ticket


@transaction.atomic
def finalize(ticket_id, payment_id, provider_payment_id=None):
    t = Ticket.objects.select_for_update().get(pk=ticket_id)
    if t.status == "paid":
        return t
    p = Payment.objects.select_for_update().get(pk=payment_id)
    p.status, p.provider_payment_id = "paid", provider_payment_id
    p.save()
    pat = Patient.objects.filter(phone=t.phone, name__iexact=t.name).order_by("id").first()
    if not pat:
        pat = Patient.objects.create(name=t.name, phone=t.phone, age=t.age, sex=t.sex, language=t.language)
        pat.uid = f"SMHS{timezone.localdate():%y%m}{pat.pk:07d}"
        pat.save(update_fields=["uid"])
    t.patient, t.status, t.paid_at = pat, "paid", timezone.now()
    t.save()
    notify.queue(t.phone, notify.text(t.language, "paid", uid=pat.uid))
    return t


@transaction.atomic
def assign(ticket, result, keys):
    d = Department.objects.select_for_update().get(code=result.dept)
    now = timezone.now()
    n = Ticket.objects.filter(department=d, triaged_at__date=timezone.localdate()).count() + 1
    ticket.department, ticket.symptoms, ticket.category = d, list(keys), result.category
    ticket.priority, ticket.escalate, ticket.token_no, ticket.triaged_at = result.priority, result.escalate, n, now
    ticket.save()
    nm = d.name_ur if ticket.language in ("ur", "ks") and d.name_ur else d.name_en
    notify.queue(ticket.phone, notify.text(ticket.language, "route", dept=nm, n=ticket.token_no))
    return ticket


@transaction.atomic
def finalize_lab(order_id, payment_id, provider_payment_id=None):
    from .models import LabOrder

    o = LabOrder.objects.select_for_update().get(pk=order_id)
    if o.paid_at:
        return o
    p = Payment.objects.select_for_update().get(pk=payment_id)
    p.status, p.provider_payment_id = "paid", provider_payment_id
    p.save()
    o.paid_at = timezone.now()
    o.save(update_fields=["paid_at"])
    return o
