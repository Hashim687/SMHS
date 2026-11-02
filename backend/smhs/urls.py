from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/", include("clinic.urls")),
]

if settings.ENABLE_DJANGO_ADMIN:
    urlpatterns.append(path(settings.ADMIN_URL, admin.site.urls))
