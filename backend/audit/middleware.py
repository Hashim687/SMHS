from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import record

SAFE = {"GET", "HEAD", "OPTIONS"}


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        p = request.path
        if p.startswith("/api/") and not p.startswith("/api/auth/") and (request.method not in SAFE or p.startswith("/api/admin/")):
            try:
                a = JWTAuthentication().authenticate(request)
                record(request, "api", a[0] if a else None, "", response.status_code)
            except Exception:
                record(request, "api", None, "", response.status_code)
        return response
