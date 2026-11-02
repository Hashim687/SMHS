from django.conf import settings
from django.db.models import Count

from accounts.models import User

from .models import Department, LabTest, StaffAssignment, TicketPrice, TriageRule


def checks():
    opd = Department.objects.filter(emergency_category="", is_active=True)
    no_rules = [d.code for d in opd.annotate(n=Count("triagerule")).filter(n=0) if d.code != "GENMED"]
    staff = User.objects.filter(is_active=True, role__in=User.STAFF_ROLES)
    clinical = User.objects.filter(is_active=True, role__in=["doctor", "nurse"])
    assigned = set(StaffAssignment.objects.values_list("user_id", flat=True))
    heads = Department.objects.filter(is_active=True, staffassignment__user__role="doctor").distinct()
    return [
        ("dept", "Departments including Medical and Surgical Emergency exist", Department.objects.filter(emergency_category__in=["medical", "surgical"]).count() == 2 and opd.exists(), f"{opd.count()} outpatient departments"),
        ("price", "Every ticket price is at least ₹10", TicketPrice.objects.count() == 2 and not TicketPrice.objects.filter(amount__lt=10).exists(), ""),
        ("rules", "Every outpatient department has triage rules", not no_rules, ", ".join(no_rules)),
        ("assign", "Every doctor and nurse is assigned to a department", all(u.pk in assigned for u in clinical), f"{sum(u.pk not in assigned for u in clinical)} unassigned"),
        ("heads", "Every department with doctors has a head", not [d.code for d in heads if not d.head_id], ", ".join(d.code for d in heads if not d.head_id)),
        ("2fa", "All staff accounts have two-factor enabled", not staff.filter(totp_enabled=False).exists(), f"{staff.filter(totp_enabled=False).count()} without"),
        ("lab_loc", "Every lab test has pay, sample and report locations", not LabTest.objects.filter(is_active=True).filter(pay_at=None).exists() and not LabTest.objects.filter(is_active=True, sample_at=None).exists() and not LabTest.objects.filter(is_active=True, report_at=None).exists(), ""),
        ("lab_price", "Lab prices have been reviewed (none left at the seed value of ₹50)", not LabTest.objects.filter(price=50).exists(), f"{LabTest.objects.filter(price=50).count()} at ₹50"),
        ("pay", "Payment gateway keys are configured and debug is off", bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and settings.RAZORPAY_WEBHOOK_SECRET) and not settings.DEBUG, ""),
        ("sms", "A real SMS gateway is configured", settings.SMS_BACKEND == "http" and bool(settings.SMS_GATEWAY_URL), settings.SMS_BACKEND),
        ("tls", "HTTPS redirect and HSTS are enabled", settings.SECURE_SSL_REDIRECT and settings.SECURE_HSTS_SECONDS > 0, ""),
        ("key", "Secret key is not the development default", not settings.SECRET_KEY.startswith("dev-only"), ""),
        ("django_admin", "Django's built-in admin console is disabled", not settings.ENABLE_DJANGO_ADMIN, ""),
    ]


RECOMMENDATIONS = [
    ("Telemedicine", "implemented", "Doctors can book video follow-ups; point TELE_BASE_URL at a self-hosted Jitsi server for privacy."),
    ("Bed availability", "implemented", "Beds per department with live free counts on the public home screen."),
    ("Ambulance tracking", "partial", "Status board only. Live GPS needs vehicle tracking devices and a feed, not included."),
    ("Insurance claim status", "implemented", "Golden Card verification and claim status (submitted, approved, rejected)."),
    ("Patient feedback", "implemented", "Star rating and comment after triage; summary under Transactions and feedback."),
    ("SMS and email notifications", "implemented", "Outbox with retry. Needs a real SMS gateway adapter and SMTP settings."),
    ("Patient OTP login and visit history", "implemented", "Patient ID plus mobile OTP unlocks past visits."),
    ("Queue display screen for waiting areas", "planned", "Large read-only token board per department."),
    ("Electronic prescriptions and pharmacy stock", "planned", "Not part of the original scope."),
    ("Backup restore drills and penetration test", "planned", "Run before go-live; see DEPLOY.md."),
]
