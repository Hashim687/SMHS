from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

r = DefaultRouter()
r.register("admin/users", views.UserViewSet, basename="users")
r.register("admin/audit", views.AuditViewSet, basename="audit")

urlpatterns = [
    path("auth/login", views.LoginView.as_view()),
    path("auth/otp", views.OtpView.as_view()),
    path("auth/refresh", TokenRefreshView.as_view()),
    path("auth/2fa/setup", views.TwoFASetupView.as_view()),
    path("auth/2fa/confirm", views.TwoFAConfirmView.as_view()),
    path("auth/me", views.MeView.as_view()),
    path("", include(r.urls)),
]
