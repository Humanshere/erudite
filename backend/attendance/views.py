from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import Course, Enrollment
from accounts.models import User
from accounts.permissions import IsAdminOrFaculty

from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, BulkAttendanceMarkSerializer


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = AttendanceRecord.objects.select_related("course", "student", "marked_by").all()

        if user.role == User.Role.STUDENT:
            return qs.filter(student=user)

        if user.role == User.Role.FACULTY:
            return qs.filter(course__faculty=user)

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

        valid_student_ids = set(
            Enrollment.objects.filter(course=course).values_list("student_id", flat=True)
        )

        saved = []
        for item in data["records"]:
            student_id = item["student_id"]
            if student_id not in valid_student_ids:
                continue

            record, _ = AttendanceRecord.objects.update_or_create(
                course=course,
                student_id=student_id,
                date=data["date"],
                defaults={
                    "status": item["status"],
                    "remark": item.get("remark", ""),
                    "marked_by": user,
                },
            )
            saved.append(record.id)

        return Response({"saved_count": len(saved), "record_ids": saved}, status=status.HTTP_200_OK)
