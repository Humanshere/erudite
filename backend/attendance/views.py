import base64
import io
from datetime import timedelta

import qrcode
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import ClassSession, Course, Enrollment
from accounts.models import User
from accounts.permissions import IsAdminOrFaculty, IsStudent

from .models import AttendanceQrSession, AttendanceRecord
from .serializers import (
    AttendanceQrScanSerializer,
    AttendanceQrSessionCreateSerializer,
    AttendanceQrSessionSerializer,
    AttendanceRecordSerializer,
    BulkAttendanceMarkSerializer,
)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = AttendanceRecord.objects.select_related("course", "class_session", "student", "marked_by").all()

        if user.role == User.Role.STUDENT:
            return qs.filter(student=user)

        if user.role == User.Role.FACULTY:
            qs = qs.filter(course__faculty=user)

        class_session_id = self.request.query_params.get("class_session")
        if class_session_id:
            qs = qs.filter(class_session_id=class_session_id)

        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)

        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(date=date)

        return qs

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "mark_bulk"]:
            return [permissions.IsAuthenticated(), IsAdminOrFaculty()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="mark-bulk")
    def mark_bulk(self, request):
        serializer = BulkAttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        course = Course.objects.filter(id=data["course_id"]).first()
        if not course:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role == User.Role.FACULTY and course.faculty_id != user.id:
            return Response({"detail": "You are not assigned to this course."}, status=status.HTTP_403_FORBIDDEN)

        class_session = None
        class_session_id = data.get("class_session_id")
        if class_session_id:
            class_session = ClassSession.objects.filter(id=class_session_id, course=course).first()
            if not class_session:
                return Response({"detail": "Class session not found for this course."}, status=status.HTTP_404_NOT_FOUND)
            if class_session.date != data["date"]:
                return Response({"detail": "Class session date must match attendance date."}, status=status.HTTP_400_BAD_REQUEST)

        valid_student_ids = set(
            Enrollment.objects.filter(course=course).values_list("student_id", flat=True)
        )

        saved = []
        for item in data["records"]:
            student_id = item["student_id"]
            if student_id not in valid_student_ids:
                continue

            lookup = {"student_id": student_id}
            if class_session:
                lookup["class_session"] = class_session
            else:
                lookup["course"] = course
                lookup["date"] = data["date"]
                lookup["class_session"] = None

            record, _ = AttendanceRecord.objects.update_or_create(
                **lookup,
                defaults={
                    "course": course,
                    "class_session": class_session,
                    "date": data["date"],
                    "status": item["status"],
                    "remark": item.get("remark", ""),
                    "marked_by": user,
                },
            )
            saved.append(record.id)

        return Response({"saved_count": len(saved), "record_ids": saved}, status=status.HTTP_200_OK)


class AttendanceQrSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceQrSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        self._finalize_expired_sessions()
        user = self.request.user
        qs = AttendanceQrSession.objects.select_related("course", "class_session", "created_by")
        if user.role == User.Role.FACULTY:
            return qs.filter(created_by=user)
        if user.role == User.Role.STUDENT:
            return qs.none()
        return qs

    def get_permissions(self):
        if self.action == "scan":
            return [permissions.IsAuthenticated(), IsStudent()]
        if self.action in ["create", "update", "partial_update", "destroy", "deactivate"]:
            return [permissions.IsAuthenticated(), IsAdminOrFaculty()]
        return super().get_permissions()

    def _build_qr_data_url(self, payload):
        qr_img = qrcode.make(payload)
        output = io.BytesIO()
        qr_img.save(output, format="PNG")
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _initialize_session_attendance(self, session):
        enrolled_student_ids = Enrollment.objects.filter(course=session.course).values_list("student_id", flat=True)
        for student_id in enrolled_student_ids:
            lookup = {"student_id": student_id}
            if session.class_session:
                lookup["class_session"] = session.class_session
            else:
                lookup["course"] = session.course
                lookup["date"] = session.date
                lookup["class_session"] = None

            AttendanceRecord.objects.update_or_create(
                **lookup,
                defaults={
                    "course": session.course,
                    "class_session": session.class_session,
                    "date": session.date,
                    "status": AttendanceRecord.Status.ABSENT,
                    "remark": "Absent (QR not scanned yet)",
                    "marked_by": session.created_by,
                },
            )

    def _finalize_session(self, session):
        if session.finalized_at:
            return

        enrolled_student_ids = Enrollment.objects.filter(course=session.course).values_list("student_id", flat=True)
        for student_id in enrolled_student_ids:
            lookup = {"student_id": student_id}
            if session.class_session:
                lookup["class_session"] = session.class_session
            else:
                lookup["course"] = session.course
                lookup["date"] = session.date
                lookup["class_session"] = None

            AttendanceRecord.objects.get_or_create(
                **lookup,
                defaults={
                    "course": session.course,
                    "class_session": session.class_session,
                    "date": session.date,
                    "status": AttendanceRecord.Status.ABSENT,
                    "remark": "Absent (QR not scanned)",
                    "marked_by": session.created_by,
                },
            )

        session.is_active = False
        session.finalized_at = timezone.now()
        session.save(update_fields=["is_active", "finalized_at"])

    def _finalize_expired_sessions(self):
        now = timezone.now()
        expired_sessions = AttendanceQrSession.objects.filter(is_active=True, ends_at__lt=now).select_related(
            "course", "created_by"
        )
        for session in expired_sessions:
            self._finalize_session(session)

    def create(self, request, *args, **kwargs):
        self._finalize_expired_sessions()
        serializer = AttendanceQrSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        class_session = None
        if data.get("class_session_id"):
            class_session = ClassSession.objects.select_related("course").filter(id=data["class_session_id"]).first()
            if not class_session:
                return Response({"detail": "Class session not found."}, status=status.HTTP_404_NOT_FOUND)
            course = class_session.course
        else:
            course = Course.objects.filter(id=data["course_id"]).first()
            if not course:
                return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role == User.Role.FACULTY and course.faculty_id != user.id:
            return Response({"detail": "You are not assigned to this course."}, status=status.HTTP_403_FORBIDDEN)

        if class_session and data.get("course_id") and int(data["course_id"]) != course.id:
            return Response({"detail": "course_id does not match class session course."}, status=status.HTTP_400_BAD_REQUEST)

        starts_at = timezone.now()
        ends_at = starts_at + timedelta(minutes=data["duration_minutes"])
        session_date = class_session.date if class_session else data.get("date", timezone.localdate())
        session = AttendanceQrSession.objects.create(
            course=course,
            class_session=class_session,
            created_by=user,
            date=session_date,
            starts_at=starts_at,
            ends_at=ends_at,
            is_active=True,
        )

        self._initialize_session_attendance(session)

        origin = request.headers.get("Origin", "http://localhost:5173")
        scan_url = f"{origin}/?attendance_token={session.token}"
        qr_payload = scan_url
        session_data = AttendanceQrSessionSerializer(session).data

        return Response(
            {
                **session_data,
                "duration_minutes": data["duration_minutes"],
                "scan_url": scan_url,
                "qr_payload": qr_payload,
                "qr_image": self._build_qr_data_url(qr_payload),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        self._finalize_expired_sessions()
        session = self.get_object()
        user = request.user
        if user.role == User.Role.FACULTY and session.created_by_id != user.id:
            return Response({"detail": "You can only deactivate your own sessions."}, status=status.HTTP_403_FORBIDDEN)

        self._finalize_session(session)
        return Response({"detail": "QR session deactivated."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="scan")
    def scan(self, request):
        self._finalize_expired_sessions()
        serializer = AttendanceQrScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        session = (
            AttendanceQrSession.objects.select_related("course", "class_session", "created_by")
            .filter(token=token)
            .first()
        )
        if not session:
            return Response({"detail": "Invalid QR token."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if now > session.ends_at and not session.finalized_at:
            self._finalize_session(session)

        if not session.is_active:
            return Response({"detail": "This QR session is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        if now < session.starts_at:
            return Response({"detail": "This QR session is not active yet."}, status=status.HTTP_400_BAD_REQUEST)
        if now > session.ends_at:
            return Response({"detail": "This QR session has expired."}, status=status.HTTP_400_BAD_REQUEST)

        student = request.user
        is_enrolled = Enrollment.objects.filter(course=session.course, student=student).exists()
        if not is_enrolled:
            return Response({"detail": "You are not enrolled in this course."}, status=status.HTTP_403_FORBIDDEN)

        lookup = {"student": student}
        if session.class_session:
            lookup["class_session"] = session.class_session
        else:
            lookup["course"] = session.course
            lookup["date"] = session.date
            lookup["class_session"] = None

        record, _ = AttendanceRecord.objects.update_or_create(
            **lookup,
            defaults={
                "course": session.course,
                "class_session": session.class_session,
                "date": session.date,
                "status": AttendanceRecord.Status.PRESENT,
                "remark": "Marked via QR scan",
                "marked_by": session.created_by,
            },
        )

        return Response(
            {
                "detail": "Attendance marked successfully.",
                "session_id": session.id,
                "record": AttendanceRecordSerializer(record).data,
            },
            status=status.HTTP_200_OK,
        )
