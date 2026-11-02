import base64
import hashlib
import hmac
import json
import urllib.request

from django.conf import settings


class PaymentUnavailable(Exception):
    pass


def mock():
    return settings.DEBUG and not settings.RAZORPAY_KEY_ID


def secret():
    return "mock-secret" if mock() else settings.RAZORPAY_KEY_SECRET


def create_order(ref_hex, amount):
    if mock():
        return {"order_id": "mock_" + ref_hex, "mock": True}
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise PaymentUnavailable
    auth = base64.b64encode(f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()).decode()
    body = json.dumps({"amount": int(amount * 100), "currency": "INR", "receipt": ref_hex[:30]}).encode()
    req = urllib.request.Request("https://api.razorpay.com/v1/orders", body,
                                 {"Content-Type": "application/json", "Authorization": "Basic " + auth})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return {"order_id": json.load(r)["id"], "mock": False}
    except Exception:
        raise PaymentUnavailable


def sign(order_id, payment_id):
    return hmac.new(secret().encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def valid(order_id, payment_id, sig):
    return bool(secret()) and hmac.compare_digest(sign(order_id, payment_id), sig)


def valid_webhook(body, sig):
    k = settings.RAZORPAY_WEBHOOK_SECRET
    return bool(k) and hmac.compare_digest(hmac.new(k.encode(), body, hashlib.sha256).hexdigest(), sig)
