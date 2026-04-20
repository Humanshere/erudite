from django.db import models

from academics.models import Course
from accounts.models import User


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
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
        unique_together = ("course", "student", "date")
        ordering = ["-date", "course_id", "student_id"]

    def __str__(self):
        return f"{self.course_id} | {self.student_id} | {self.date} | {self.status}"
