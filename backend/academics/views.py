from datetime import timedelta

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status

from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrFaculty

from .models import ClassSession, Course, Department, Enrollment, Semester
from .serializers import (
    AutoScheduleClassSessionSerializer,
    ClassSessionSerializer,
    CourseSerializer,
    DepartmentSerializer,
    EnrollmentSerializer,
    SemesterSerializer,
)


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


class ClassSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ClassSession.objects.select_related("course", "faculty", "created_by").all()
        user = self.request.user

        if user.role == User.Role.FACULTY:
            return qs.filter(faculty=user)

        if user.role == User.Role.STUDENT:
            return qs.filter(course__enrollments__student=user).distinct()

        return qs

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "auto_schedule", "unschedule"]:
            return [permissions.IsAuthenticated(), IsAdminOrFaculty()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        course = serializer.validated_data["course"]

        if user.role == User.Role.FACULTY and course.faculty_id != user.id:
            raise PermissionDenied("You are not assigned to this course.")

        session_type = serializer.validated_data.get("session_type") or ClassSession.SessionType.EXTRA
        serializer.save(
            faculty=course.faculty,
            created_by=user,
            session_type=session_type,
            is_auto_generated=False,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        course = serializer.validated_data["course"]
        if user.role == User.Role.FACULTY and course.faculty_id != user.id:
            raise PermissionDenied("You are not assigned to this course.")

        date = serializer.validated_data["date"]
        start_time = serializer.validated_data["start_time"]
        existing = ClassSession.objects.filter(course=course, date=date, start_time=start_time).first()

        if existing:
            if existing.status == ClassSession.Status.CANCELLED:
                existing.end_time = serializer.validated_data["end_time"]
                existing.session_type = serializer.validated_data.get("session_type", ClassSession.SessionType.EXTRA)
                existing.status = serializer.validated_data.get("status", ClassSession.Status.SCHEDULED)
                existing.note = serializer.validated_data.get("note", "")
                existing.faculty = course.faculty
                existing.created_by = user
                existing.is_auto_generated = False
                existing.save()
                output = self.get_serializer(existing)
                return Response(output.data, status=status.HTTP_200_OK)

            return Response(
                {"detail": "A class already exists for this course at the same date and start time."},
                status=status.HTTP_409_CONFLICT,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["post"], url_path="auto-schedule")
    def auto_schedule(self, request):
        serializer = AutoScheduleClassSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        course = Course.objects.filter(id=data["course_id"]).first()
        if not course:
            return Response({"detail": "Course not found."}, status=404)

        user = request.user
        if user.role == User.Role.FACULTY and course.faculty_id != user.id:
            return Response({"detail": "You are not assigned to this course."}, status=403)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        current_date = data["start_date"]
        while current_date <= data["end_date"]:
            if current_date.weekday() in data["weekdays"]:
                defaults = {
                    "end_time": data["end_time"],
                    "session_type": ClassSession.SessionType.REGULAR,
                    "is_auto_generated": True,
                    "status": ClassSession.Status.SCHEDULED,
                    "faculty": course.faculty,
                    "created_by": user,
                    "note": "Auto-scheduled class",
                }

                existing = ClassSession.objects.filter(
                    course=course,
                    date=current_date,
                    start_time=data["start_time"],
                ).first()

                if existing:
                    if existing.status == ClassSession.Status.CANCELLED or data["replace_existing"]:
                        for key, value in defaults.items():
                            setattr(existing, key, value)
                        existing.save()
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    ClassSession.objects.create(
                        course=course,
                        date=current_date,
                        start_time=data["start_time"],
                        **defaults,
                    )
                    created_count += 1

            current_date += timedelta(days=1)

        return Response(
            {
                "detail": "Auto scheduling complete.",
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
            }
        )

    @action(detail=True, methods=["post"], url_path="unschedule")
    def unschedule(self, request, pk=None):
        session = self.get_object()
        if session.status == ClassSession.Status.CANCELLED:
            return Response({"detail": "Class is already unscheduled."}, status=400)

        note = (request.data.get("note") or "").strip()
        session.status = ClassSession.Status.CANCELLED
        session.note = note or "Unscheduled by faculty"
        session.save(update_fields=["status", "note"])

        return Response({"detail": "Class unscheduled successfully."})
