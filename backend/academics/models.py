from django.db import models

from accounts.models import User


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Semester(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    credits = models.PositiveSmallIntegerField(default=3)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="courses")
    faculty = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_courses",
        limit_choices_to={"role": "faculty"},
    )

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "student"},
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student_id} -> {self.course_id}"


class ClassSession(models.Model):
    class SessionType(models.TextChoices):
        REGULAR = "regular", "Regular"
        EXTRA = "extra", "Extra"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="class_sessions")
    faculty = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_sessions",
        limit_choices_to={"role": "faculty"},
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    session_type = models.CharField(max_length=10, choices=SessionType.choices, default=SessionType.REGULAR)
    is_auto_generated = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_class_sessions",
        limit_choices_to={"role__in": ["admin", "faculty"]},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "date", "start_time")
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.course_id} | {self.date} {self.start_time}-{self.end_time}"
