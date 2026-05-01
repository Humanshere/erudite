from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClassSessionViewSet, CourseViewSet, DepartmentViewSet, EnrollmentViewSet, SemesterViewSet

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"semesters", SemesterViewSet, basename="semester")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")
router.register(r"class-sessions", ClassSessionViewSet, basename="class-session")

urlpatterns = [
    path("", include(router.urls)),
]
