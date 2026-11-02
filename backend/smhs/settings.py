import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
E = os.environ.get
SECRET_KEY = E("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = E("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = E("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in E("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
if E("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(E("RENDER_EXTERNAL_HOSTNAME"))
    CSRF_TRUSTED_ORIGINS.append("https://" + E("RENDER_EXTERNAL_HOSTNAME"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "audit",
    "clinic",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "audit.middleware.AuditMiddleware",
]
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
except ImportError:
    pass
FRONTEND_DIR = BASE_DIR / "frontend_dist"
if FRONTEND_DIR.is_dir():
    WHITENOISE_ROOT = FRONTEND_DIR
    WHITENOISE_INDEX_FILE = True
ROOT_URLCONF = "smhs.urls"
WSGI_APPLICATION = "smhs.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

if E("DATABASE_URL"):
    from urllib.parse import parse_qs, unquote, urlparse
    _u = urlparse(E("DATABASE_URL"))
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _u.path.lstrip("/"),
        "USER": unquote(_u.username or ""),
        "PASSWORD": unquote(_u.password or ""),
        "HOST": _u.hostname,
        "PORT": _u.port or 5432,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"sslmode": parse_qs(_u.query).get("sslmode", ["require"])[0]},
    }}
elif E("USE_SQLITE") == "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": E("DB_NAME", "smhs"),
        "USER": E("DB_USER", "smhs"),
        "PASSWORD": E("DB_PASSWORD", ""),
        "HOST": E("DB_HOST", "db"),
        "PORT": E("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }}

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ur", "Urdu"), ("ks", "Kashmiri")]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "NUM_PROXIES": int(E("NUM_PROXIES", "0")),
    "DEFAULT_THROTTLE_RATES": {"anon": "600/min", "user": "2400/min", "login": "10/min", "otp": "10/min", "ticket": "20/min", "symptoms": "30/min"},
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=8),
    "ROTATE_REFRESH_TOKENS": True,
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
ADMIN_URL = E("ADMIN_URL", "api/hms-console/")
ENABLE_DJANGO_ADMIN = E("ENABLE_DJANGO_ADMIN", "0") == "1"
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
RAZORPAY_KEY_ID = E("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = E("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = E("RAZORPAY_WEBHOOK_SECRET", "")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "cache_table"}}
SMS_BACKEND = E("SMS_BACKEND", "console")
SMS_GATEWAY_URL = E("SMS_GATEWAY_URL", "")
SMS_GATEWAY_KEY = E("SMS_GATEWAY_KEY", "")
SMS_SENDER = E("SMS_SENDER", "SMHSSR")
EMAIL_HOST = E("EMAIL_HOST", "localhost")
EMAIL_PORT = int(E("EMAIL_PORT", "25"))
EMAIL_HOST_USER = E("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = E("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = E("EMAIL_USE_TLS", "0") == "1"
DEFAULT_FROM_EMAIL = E("DEFAULT_FROM_EMAIL", "no-reply@smhs.local")
TELE_BASE_URL = E("TELE_BASE_URL", "https://meet.jit.si")
