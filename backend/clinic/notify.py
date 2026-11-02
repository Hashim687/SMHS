import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification

log = logging.getLogger("smhs.notify")
SENT = []
T = {
    "paid": {"en": "SMHS Srinagar: payment received. Your Patient ID is {uid}.", "ur": "ایس ایم ایچ ایس سرینگر: ادائیگی موصول ہوئی۔ آپ کا مریض آئی ڈی {uid} ہے۔"},
    "route": {"en": "SMHS: please go to {dept}. Your token number is {n}.", "ur": "ایس ایم ایچ ایس: براہِ کرم {dept} جائیں۔ آپ کا ٹوکن نمبر {n} ہے۔"},
    "report": {"en": "SMHS: your lab report is ready. Collect it at the report counter or download it from the portal.", "ur": "ایس ایم ایچ ایس: آپ کی لیب رپورٹ تیار ہے۔ رپورٹ کاؤنٹر سے لیں یا پورٹل سے ڈاؤن لوڈ کریں۔"},
    "admit": {"en": "SMHS: admission confirmed. Ward/bed: {ward}.", "ur": "ایس ایم ایچ ایس: داخلہ منظور ہو گیا۔ وارڈ/بستر: {ward}۔"},
    "reject": {"en": "SMHS: admission was not confirmed. Please speak to your doctor.", "ur": "ایس ایم ایچ ایس: داخلہ منظور نہیں ہوا۔ براہِ کرم اپنے ڈاکٹر سے بات کریں۔"},
    "appt": {"en": "SMHS: follow-up booked for {when}.", "ur": "ایس ایم ایچ ایس: فالو اپ {when} کو بُک ہو گیا۔"},
    "golden": {"en": "SMHS: your Golden Card was {status}.", "ur": "ایس ایم ایچ ایس: آپ کا گولڈن کارڈ {status}۔"},
    "otp": {"en": "SMHS OTP: {code}. Valid for 5 minutes. Do not share it.", "ur": "ایس ایم ایچ ایس او ٹی پی: {code}۔ 5 منٹ کے لیے درست ہے۔ کسی کو نہ بتائیں۔"},
}


def text(lang, key, **kw):
    d = T[key]
    return d["ur" if lang in ("ur", "ks") else "en"].format(**kw)


def deliver(n):
    n.attempts += 1
    try:
        b = settings.SMS_BACKEND
        if n.channel == "email":
            send_mail(n.subject, n.text, None, [n.to])
        elif b == "memory":
            SENT.append((n.to, n.text))
        elif b == "console" and settings.DEBUG:
            log.info("SMS to %s: %s", n.to, n.text)
        elif b == "http" and settings.SMS_GATEWAY_URL:
            body = json.dumps({"to": n.to, "message": n.text, "sender": settings.SMS_SENDER}).encode()
            req = urllib.request.Request(settings.SMS_GATEWAY_URL, body, {"Content-Type": "application/json", "Authorization": "Bearer " + settings.SMS_GATEWAY_KEY})
            urllib.request.urlopen(req, timeout=10).close()
        else:
            raise RuntimeError("no_backend")
        n.status, n.sent_at = "sent", timezone.now()
        if n.redact:
            n.text = "[redacted]"
    except Exception:
        log.warning("notification %s failed", n.pk)
        n.status = "failed" if n.attempts >= 5 else "pending"
    n.save()


def queue(to, body, channel="sms", subject="", secret=False, now=False):
    n = Notification.objects.create(to=to, channel=channel, subject=subject[:120], text=body, redact=secret)
    if now:
        deliver(n)
    return n
