import base64
import json
import logging
import re
import urllib.parse
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
        elif b == "console":
            log.warning("SMS to %s: %s", n.to, n.text if not n.redact or settings.DEBUG or settings.DEMO_SHOW_OTP else "[hidden]")
        elif b == "twilio" and settings.TWILIO_SID:
            to = n.to if n.to.startswith("+") else settings.SMS_COUNTRY_CODE + n.to
            data = urllib.parse.urlencode({"To": to, "From": settings.TWILIO_FROM, "Body": n.text}).encode()
            req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_SID}/Messages.json", data)
            req.add_header("Authorization", "Basic " + base64.b64encode(f"{settings.TWILIO_SID}:{settings.TWILIO_TOKEN}".encode()).decode())
            urllib.request.urlopen(req, timeout=15).close()
        elif b == "fast2sms" and settings.FAST2SMS_KEY:
            if settings.FAST2SMS_ROUTE == "otp":
                m = re.search(r"\b(\d{4,8})\b", n.text)
                if not m:
                    raise RuntimeError("fast2sms otp route sends only OTP messages")
                form = {"route": "otp", "variables_values": m.group(1), "numbers": n.to[-10:]}
            else:
                form = {"route": settings.FAST2SMS_ROUTE, "message": n.text, "numbers": n.to[-10:]}
            req = urllib.request.Request("https://www.fast2sms.com/dev/bulkV2", urllib.parse.urlencode(form).encode(), {"authorization": settings.FAST2SMS_KEY})
            urllib.request.urlopen(req, timeout=15).close()
        elif b == "http" and settings.SMS_GATEWAY_URL:
            body = json.dumps({"to": n.to, "message": n.text, "sender": settings.SMS_SENDER}).encode()
            req = urllib.request.Request(settings.SMS_GATEWAY_URL, body, {"Content-Type": "application/json", "Authorization": "Bearer " + settings.SMS_GATEWAY_KEY})
            urllib.request.urlopen(req, timeout=10).close()
        else:
            raise RuntimeError("no_backend")
        n.status, n.sent_at = "sent", timezone.now()
        if n.redact:
            n.text = "[redacted]"
    except Exception as e:
        log.warning("notification %s failed: %s", n.pk, type(e).__name__ + (": " + str(e)[:120] if not n.redact else ""))
        n.status = "failed" if n.attempts >= 5 else "pending"
    n.save()


def queue(to, body, channel="sms", subject="", secret=False, now=False):
    n = Notification.objects.create(to=to, channel=channel, subject=subject[:120], text=body, redact=secret)
    if now:
        deliver(n)
    return n
