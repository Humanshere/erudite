from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceQrSessionViewSet, AttendanceRecordViewSet

router = DefaultRouter()
router.register(r"records", AttendanceRecordViewSet, basename="attendance-record")
router.register(r"qr-sessions", AttendanceQrSessionViewSet, basename="attendance-qr-session")

urlpatterns = [
    path("", include(router.urls)),
]
