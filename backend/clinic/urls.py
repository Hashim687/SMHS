from django.urls import include, path, register_converter


class Hex:
    regex = "[0-9a-f]{32}"

    def to_python(self, v):
        return v

    def to_url(self, v):
        return v


register_converter(Hex, "hex")
from rest_framework.routers import DefaultRouter

from . import views as v
from . import extras as x
from . import lab as l
from . import ward as w

r = DefaultRouter()
r.register("admin/departments", v.DepartmentAdmin, basename="adm-dept")
r.register("admin/prices", v.PriceAdmin, basename="adm-price")
r.register("admin/symptoms", v.SymptomAdmin, basename="adm-sym")
r.register("admin/triage-rules", v.RuleAdmin, basename="adm-rule")
r.register("admin/locations", v.LocationAdmin, basename="adm-loc")
r.register("admin/lab-tests", v.LabTestAdmin, basename="adm-lab")
r.register("admin/beds", v.BedAdmin, basename="adm-bed")
r.register("admin/translations", v.TextAdmin, basename="adm-text")
r.register("admin/feedback", v.FeedbackAdmin, basename="adm-fb")
r.register("admin/notifications", v.NotificationAdmin, basename="adm-note")
r.register("staff/ambulances", v.AmbulanceAdmin, basename="amb")
r.register("admin/staff-assignments", v.AssignmentAdmin, basename="adm-assign")

urlpatterns = [
    path("public/departments", v.Departments.as_view()),
    path("public/symptoms", v.Symptoms.as_view()),
    path("public/prices", v.Prices.as_view()),
    path("public/tickets", v.TicketCreateView.as_view()),
    path("public/tickets/<hex:ref>", v.TicketStatus.as_view()),
    path("public/tickets/<hex:ref>/verify", v.TicketVerify.as_view()),
    path("public/tickets/<hex:ref>/symptoms", v.TicketSymptoms.as_view()),
    path("payments/razorpay/webhook", v.Webhook.as_view()),
    path("staff/tickets/cash", v.CashTicket.as_view()),
    path("staff/emergency-queue", v.EmergencyQueue.as_view()),
    path("staff/lab-catalog", l.Catalog.as_view()),
    path("staff/patients/<int:pk>/lab-orders", l.OrderTests.as_view()),
    path("staff/patients/<int:pk>/lab", l.PatientLab.as_view()),
    path("staff/patients/<int:pk>/appointments", l.Appoint.as_view()),
    path("staff/lab-orders/<int:pk>/report.pdf", l.StaffPdf.as_view()),
    path("staff/lab-orders/unpaid", l.CashLab.as_view()),
    path("staff/lab-orders/<int:pk>/cash", l.CashLab.as_view()),
    path("lab/queue", l.LabQueue.as_view()),
    path("lab/ready", l.Ready.as_view()),
    path("lab/items/<int:pk>/collect", l.Collect.as_view()),
    path("lab/items/<int:pk>/result", l.Result.as_view()),
    path("lab/orders/<int:pk>/handover", l.Handover.as_view()),
    path("public/tickets/<hex:ref>/portal", l.PortalView.as_view()),
    path("public/lab-orders/<hex:oref>/pay", l.LabPay.as_view()),
    path("public/lab-orders/<hex:oref>/verify", l.LabVerify.as_view()),
    path("public/lab-orders/<hex:oref>/report.pdf", l.PublicPdf.as_view()),
    path("public/tickets/<hex:ref>/golden-card", x.GoldenSubmit.as_view()),
    path("public/tickets/<hex:ref>/feedback", x.FeedbackSubmit.as_view()),
    path("public/patient/otp/request", x.OtpRequest.as_view()),
    path("public/patient/otp/verify", x.OtpVerify.as_view()),
    path("public/patient/history", x.History.as_view()),
    path("public/beds", x.BedsPublic.as_view()),
    path("public/ambulances", x.AmbulancesPublic.as_view()),
    path("public/translations/<str:lang>", x.Translations.as_view()),
    path("staff/golden-cards", x.GoldenList.as_view()),
    path("staff/golden-cards/<int:pk>/decide", x.GoldenDecide.as_view()),
    path("staff/golden-cards/<int:pk>/claim", x.GoldenClaim.as_view()),
    path("staff/beds/free", x.FreeBeds.as_view()),
    path("admin/transactions", x.Transactions.as_view()),
    path("admin/self-review", x.SelfReview.as_view()),
    path("staff/profile", w.Profile.as_view()),
    path("staff/patients", w.Patients.as_view()),
    path("staff/patients/history/<str:uid>", w.History.as_view()),
    path("staff/patients/<int:pk>/status", w.SetStatus.as_view()),
    path("staff/patients/<int:pk>/claim", w.Claim.as_view()),
    path("staff/patients/<int:pk>/admit-request", w.AdmitRequest.as_view()),
    path("staff/admissions", w.Admissions.as_view()),
    path("staff/admissions/<int:pk>/decide", w.Decide.as_view()),
    path("staff/admissions/<int:pk>/discharge", w.Discharge.as_view()),
    path("", include(r.urls)),
]
