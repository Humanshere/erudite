import uuid

from django.db import models
from django.utils import timezone

from academics.models import ClassSession, Course
from accounts.models import User


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
    class_session = models.ForeignKey(
        ClassSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role": "student"},
    )
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendance",
        limit_choices_to={"role__in": ["admin", "faculty"]},
    )
    date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices)
    remark = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date", "course_id", "class_session_id", "student_id"]
        unique_together = ("class_session", "student")

    def __str__(self):
        return f"{self.course_id} | {self.student_id} | {self.date} | {self.status}"


class AttendanceQrSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_qr_sessions")
    class_session = models.ForeignKey(
        ClassSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_qr_sessions",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_attendance_qr_sessions",
        limit_choices_to={"role__in": ["admin", "faculty"]},
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    date = models.DateField()
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"QR {self.course_id} | {self.date} | {self.token}"
