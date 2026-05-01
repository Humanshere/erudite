from rest_framework import serializers

from .models import ClassSession, Course, Department, Enrollment, Semester


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    semester_name = serializers.CharField(source="semester.name", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "code",
            "title",
            "credits",
            "department",
            "department_name",
            "semester",
            "semester_name",
            "faculty",
            "faculty_name",
        )


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student",
            "student_name",
            "student_email",
            "course",
            "course_code",
            "course_title",
            "enrolled_at",
        )


class ClassSessionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    faculty_name = serializers.CharField(source="faculty.full_name", read_only=True)

    class Meta:
        model = ClassSession
        fields = (
            "id",
            "course",
            "course_code",
            "course_title",
            "faculty",
            "faculty_name",
            "date",
            "start_time",
            "end_time",
            "session_type",
            "is_auto_generated",
            "status",
            "note",
            "created_by",
            "created_at",
        )
        read_only_fields = ("is_auto_generated", "faculty", "created_by", "created_at")

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("End time must be after start time.")
        return attrs


class AutoScheduleClassSessionSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), allow_empty=False)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    replace_existing = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError("End date must be on or after start date.")
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("End time must be after start time.")
        attrs["weekdays"] = sorted(set(attrs["weekdays"]))
        return attrs
