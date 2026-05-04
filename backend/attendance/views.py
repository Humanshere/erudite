import base64
import io
import math
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


def _distance_meters(lat1, lon1, lat2, lon2):
    radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
            faculty_latitude=data["faculty_latitude"],
            faculty_longitude=data["faculty_longitude"],
            faculty_location_accuracy=data.get("faculty_location_accuracy"),
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
        def scan_log(message):
            print(f"[QR Scan] {message}")

        scan_log(f"Request received from user={request.user.id} role={getattr(request.user, 'role', None)}")
        scan_log(f"Incoming keys={sorted(list(request.data.keys()))}")
        self._finalize_expired_sessions()
        scan_log("Expired sessions checked")

        serializer = AttendanceQrScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        scan_log(f"Payload validated token={str(token)[:8]}...")

        # Enforce mandatory anti-proxy fields
        if "latitude" not in serializer.validated_data or "longitude" not in serializer.validated_data:
            scan_log("Rejected: latitude/longitude missing")
            return Response({"detail": "Location (latitude and longitude) is required."}, status=status.HTTP_400_BAD_REQUEST)
        has_selfie = "selfie" in serializer.validated_data or request.FILES.get("selfie")
        if not has_selfie:
            scan_log("Rejected: selfie missing")
            return Response({"detail": "Selfie image is required."}, status=status.HTTP_400_BAD_REQUEST)

        scan_log("Looking up QR session by token")
        session = (
            AttendanceQrSession.objects.select_related("course", "class_session", "created_by")
            .filter(token=token)
            .first()
        )
        if not session:
            scan_log("Rejected: invalid QR token")
            return Response({"detail": "Invalid QR token."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        scan_log(
            f"Session found id={session.id} course={session.course_id} class_session={session.class_session_id} active={session.is_active} now={now.isoformat()} ends_at={session.ends_at.isoformat()}"
        )
        if now > session.ends_at and not session.finalized_at:
            scan_log("Session expired, finalizing before proceeding")
            self._finalize_session(session)

        if not session.is_active:
            scan_log("Rejected: session inactive")
            return Response({"detail": "This QR session is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        if now < session.starts_at:
            scan_log("Rejected: session not active yet")
            return Response({"detail": "This QR session is not active yet."}, status=status.HTTP_400_BAD_REQUEST)
        if now > session.ends_at:
            scan_log("Rejected: session expired")
            return Response({"detail": "This QR session has expired."}, status=status.HTTP_400_BAD_REQUEST)

        student = request.user
        latitude = serializer.validated_data.get("latitude")
        longitude = serializer.validated_data.get("longitude")
        distance = _distance_meters(session.faculty_latitude, session.faculty_longitude, latitude, longitude)
        scan_log(
            f"Location received latitude={latitude} longitude={longitude} session_center=({session.faculty_latitude}, {session.faculty_longitude}) distance={distance:.2f}m"
        )
        
        # Use session's faculty_location_accuracy as the allowed radius (default to 40m if not set)
        allowed_radius = session.faculty_location_accuracy or 40
        scan_log(f"Allowed radius={allowed_radius}m")
        if distance > allowed_radius:
            scan_log("Rejected: outside allowed radius")
            return Response(
                {"detail": f"You are outside the allowed {allowed_radius}m radius for this QR session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Face verification: ensure student has a benchmark and the selfie matches
        # Get student's benchmark encoding
        student_benchmark = getattr(student, "benchmark_face_encoding", None)
        if not student_benchmark:
            scan_log("Rejected: no benchmark face encoding found for student")
            return Response({"detail": "No benchmark selfie found. Upload benchmark selfie before scanning."}, status=status.HTTP_400_BAD_REQUEST)

        # load selfie from request.FILES or validated_data
        selfie_file = serializer.validated_data.get("selfie") if "selfie" in serializer.validated_data else None
        if not selfie_file and request.FILES.get("selfie"):
            selfie_file = request.FILES.get("selfie")

        if not selfie_file:
            scan_log("Rejected: selfie file missing after validation")
            return Response({"detail": "Selfie is required for face verification."}, status=status.HTTP_400_BAD_REQUEST)

        # compress and compute encoding for uploaded selfie
        try:
            from PIL import Image
            import io
            import face_recognition

            scan_log(f"Starting face verification for user={student.id}")
            
            img = Image.open(selfie_file)
            # respect EXIF orientation
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            max_dim = 800
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            buf.seek(0)
            
            scan_log(f"Loading selfie image size={img.size}")
            uploaded_np = face_recognition.load_image_file(buf)
            scan_log(f"Selfie image loaded shape={uploaded_np.shape}")
            
            # try hog then cnn fallback for robustness
            scan_log("Detecting face encodings")
            uploaded_encs = face_recognition.face_encodings(uploaded_np)
            
            if not uploaded_encs:
                scan_log("No encodings found initially, trying HOG face detection")
                locs_hog = face_recognition.face_locations(uploaded_np, model="hog")
                scan_log(f"HOG detected {len(locs_hog)} faces")
                
                if not locs_hog:
                    try:
                        scan_log("No HOG faces, trying CNN detection")
                        locs_cnn = face_recognition.face_locations(uploaded_np, model="cnn")
                        scan_log(f"CNN detected {len(locs_cnn)} faces")
                        if locs_cnn:
                            uploaded_encs = face_recognition.face_encodings(uploaded_np, known_face_locations=locs_cnn)
                    except Exception as ex:
                        scan_log(f"CNN failed: {str(ex)}")
            
            if not uploaded_encs:
                scan_log("Rejected: no face detected in selfie")
                return Response({"detail": "No face detected in the selfie."}, status=status.HTTP_400_BAD_REQUEST)
            
            uploaded_enc = uploaded_encs[0]
            scan_log("Face encoded successfully")

            # compare with stored benchmark
            import numpy as _np
            benchmark_enc = _np.array(student_benchmark)
            dist = float(_np.linalg.norm(benchmark_enc - uploaded_enc))
            scan_log(f"Face distance={dist:.4f}")
            
            # threshold: 0.6 is common; use 0.5 for stricter matching
            if dist > 0.5:
                scan_log(f"Rejected: face mismatch distance={dist:.4f} threshold=0.5")
                return Response({"detail": "Face did not match benchmark."}, status=status.HTTP_403_FORBIDDEN)
            
            scan_log("Face matched successfully")
        except Exception as ex:
            scan_log(f"Exception during face verification: {str(ex)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Face verification failed: {str(ex)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        scan_log("Checking enrollment")
        is_enrolled = Enrollment.objects.filter(course=session.course, student=student).exists()
        if not is_enrolled:
            scan_log("Rejected: student not enrolled in course")
            return Response({"detail": "You are not enrolled in this course."}, status=status.HTTP_403_FORBIDDEN)

        scan_log("Creating or updating attendance record")
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
                "remark": f"Marked via QR scan ({distance:.1f}m from QR center)",
                "marked_by": session.created_by,
            },
        )
        scan_log(f"Attendance record saved id={record.id} status={record.status}")

        # Save optional location/selfie metadata if provided
        latitude = serializer.validated_data.get("latitude")
        longitude = serializer.validated_data.get("longitude")
        accuracy = serializer.validated_data.get("accuracy")
        selfie = serializer.validated_data.get("selfie") if "selfie" in serializer.validated_data else None
        # uploaded files may also appear in request.FILES
        if not selfie and request.FILES.get("selfie"):
            selfie = request.FILES.get("selfie")

        dirty = False
        if latitude is not None:
            record.latitude = latitude
            dirty = True
        if longitude is not None:
            record.longitude = longitude
            dirty = True
        if accuracy is not None:
            record.accuracy = accuracy
            dirty = True
        if selfie is not None:
            record.selfie = selfie
            dirty = True
        if dirty:
            scan_log("Saving optional metadata on attendance record")
            record.save()

        scan_log("QR scan processing completed successfully")

        return Response(
            {
                "detail": "Attendance marked successfully.",
                "session_id": session.id,
                "record": AttendanceRecordSerializer(record).data,
            },
            status=status.HTTP_200_OK,
        )
