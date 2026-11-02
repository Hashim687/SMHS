import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

PHONE = RegexValidator(r"^[6-9]\d{9}$")


class Department(models.Model):
    code = models.CharField(max_length=12, unique=True)
    name_en = models.CharField(max_length=80)
    name_ur = models.CharField(max_length=80, blank=True)
    name_ks = models.CharField(max_length=80, blank=True)
    head = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="headed")
    emergency_category = models.CharField(max_length=8, blank=True, choices=[("medical", "medical"), ("surgical", "surgical")])
    is_active = models.BooleanField(default=True)


class TicketPrice(models.Model):
    kind = models.CharField(max_length=10, primary_key=True, choices=[("opd", "opd"), ("emergency", "emergency")])
    amount = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(10)])


class Symptom(models.Model):
    key = models.SlugField(unique=True)
    icon = models.CharField(max_length=8)
    emergency_category = models.CharField(max_length=8, blank=True, choices=[("medical", "medical"), ("surgical", "surgical")])
    severity = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)


class TriageRule(models.Model):
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE, related_name="rules")
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("symptom", "department")


class Patient(models.Model):
    uid = models.CharField(max_length=16, unique=True, null=True, blank=True)
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=10, validators=[PHONE], db_index=True)
    age = models.PositiveSmallIntegerField()
    sex = models.CharField(max_length=1)
    language = models.CharField(max_length=2, default="en")
    created = models.DateTimeField(auto_now_add=True)


class Ticket(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=10)
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=10)
    age = models.PositiveSmallIntegerField()
    sex = models.CharField(max_length=1)
    language = models.CharField(max_length=2, default="en")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=8, default="pending", db_index=True)
    patient = models.ForeignKey(Patient, null=True, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, null=True, on_delete=models.PROTECT)
    symptoms = models.JSONField(default=list)
    category = models.CharField(max_length=8, blank=True)
    priority = models.PositiveSmallIntegerField(null=True)
    escalate = models.BooleanField(default=False)
    token_no = models.PositiveIntegerField(null=True)
    state = models.CharField(max_length=12, default="waiting")
    nurse = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True)
    triaged_at = models.DateTimeField(null=True, db_index=True)


class Payment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT)
    method = models.CharField(max_length=8)
    provider_order_id = models.CharField(max_length=64, blank=True, db_index=True)
    provider_payment_id = models.CharField(max_length=64, null=True, unique=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=8, default="created")
    lab_order = models.ForeignKey("LabOrder", null=True, blank=True, on_delete=models.PROTECT)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)


class StaffAssignment(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment")
    department = models.ForeignKey(Department, on_delete=models.CASCADE)


class Admission(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="admissions")
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=10, default="requested", db_index=True)
    ward = models.CharField(max_length=40, blank=True)
    bed = models.ForeignKey("Bed", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True)
    discharged_at = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["ticket"], condition=models.Q(status__in=["requested", "admitted"]), name="one_active_admission"),
                       models.UniqueConstraint(fields=["bed"], condition=models.Q(status="admitted"), name="one_admitted_per_bed")]


class StatusUpdate(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="updates")
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=12)
    note = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)


class Location(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name_en = models.CharField(max_length=100)
    name_ur = models.CharField(max_length=100, blank=True)
    name_ks = models.CharField(max_length=100, blank=True)


class LabTest(models.Model):
    code = models.CharField(max_length=12, unique=True)
    name_en = models.CharField(max_length=80)
    name_ur = models.CharField(max_length=80, blank=True)
    name_ks = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=16, blank=True)
    ref_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ref_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    turnaround_minutes = models.PositiveSmallIntegerField(default=60)
    per_sample_minutes = models.PositiveSmallIntegerField(default=5)
    pay_at = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    sample_at = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    report_at = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_active = models.BooleanField(default=True)


class LabOrder(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="lab_orders")
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    total = models.DecimalField(max_digits=9, decimal_places=2)
    paid_at = models.DateTimeField(null=True, db_index=True)
    handed_at = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)


class LabItem(models.Model):
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="items")
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, default="ordered", db_index=True)
    collected_at = models.DateTimeField(null=True)
    resulted_at = models.DateTimeField(null=True)
    value = models.DecimalField(max_digits=12, decimal_places=3, null=True)
    text = models.CharField(max_length=200, blank=True)
    note = models.CharField(max_length=200, blank=True)
    resulted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")


class Appointment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    scheduled_at = models.DateTimeField(db_index=True)
    mode = models.CharField(max_length=10, default="in_person")
    meeting_url = models.CharField(max_length=200, blank=True)
    note = models.CharField(max_length=200, blank=True)


class GoldenCard(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="golden")
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    number_enc = models.CharField(max_length=300)
    last4 = models.CharField(max_length=4)
    holder = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=10, default="pending", db_index=True)
    claim_status = models.CharField(max_length=10, default="none")
    note = models.CharField(max_length=200, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)


class PatientOTP(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64)
    expires = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    to = models.CharField(max_length=120)
    channel = models.CharField(max_length=5, default="sms")
    subject = models.CharField(max_length=120, blank=True)
    text = models.TextField()
    redact = models.BooleanField(default=False)
    status = models.CharField(max_length=8, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)


class TextOverride(models.Model):
    lang = models.CharField(max_length=2, choices=[("en", "en"), ("ur", "ur"), ("ks", "ks")])
    key = models.CharField(max_length=120, validators=[RegexValidator(r"^[A-Za-z0-9_.]+$")])
    value = models.CharField(max_length=300)

    class Meta:
        unique_together = ("lang", "key")


class Bed(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    label = models.CharField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("department", "label")


class Ambulance(models.Model):
    label = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=12, default="available", choices=[(x, x) for x in ("available", "dispatched", "at_scene", "returning", "offline")])
    note = models.CharField(max_length=120, blank=True)
    updated = models.DateTimeField(auto_now=True)


class Feedback(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=300, blank=True)
    created = models.DateTimeField(auto_now_add=True)
