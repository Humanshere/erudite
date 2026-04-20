from rest_framework import permissions, viewsets

from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrFaculty

from .models import Course, Department, Enrollment, Semester
from .serializers import CourseSerializer, DepartmentSerializer, EnrollmentSerializer, SemesterSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all().order_by("-start_date")
    serializer_class = SemesterSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related("department", "semester", "faculty").all().order_by("code")
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == User.Role.FACULTY:
            return qs.filter(faculty=user)
        return qs


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrFaculty]

    def get_queryset(self):
        qs = Enrollment.objects.select_related("student", "course").all().order_by("-enrolled_at")
        user = self.request.user
        if user.role == User.Role.FACULTY:
            return qs.filter(course__faculty=user)
        return qs
