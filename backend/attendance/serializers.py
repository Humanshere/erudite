from django.utils import timezone
from rest_framework import serializers

from .models import AttendanceQrSession, AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    class_session_start_time = serializers.TimeField(source="class_session.start_time", read_only=True)
    class_session_end_time = serializers.TimeField(source="class_session.end_time", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            "id",
            "course",
            "course_code",
            "course_title",
            "class_session",
            "class_session_start_time",
            "class_session_end_time",
            "student",
            "marked_by",
            "date",
            "status",
            "remark",
        )


class BulkAttendanceMarkItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    remark = serializers.CharField(required=False, allow_blank=True)


class BulkAttendanceMarkSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    date = serializers.DateField()
    class_session_id = serializers.IntegerField(required=False, allow_null=True)
    records = BulkAttendanceMarkItemSerializer(many=True)


class AttendanceQrSessionCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(required=False)
    class_session_id = serializers.IntegerField(required=False)
    date = serializers.DateField(required=False)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=240, default=10)

    def validate(self, attrs):
        if not attrs.get("course_id") and not attrs.get("class_session_id"):
            raise serializers.ValidationError("Either course_id or class_session_id is required.")
        return attrs

    def validate_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Date cannot be in the past.")
        return value


class AttendanceQrSessionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    class_session_start_time = serializers.TimeField(source="class_session.start_time", read_only=True)
    class_session_end_time = serializers.TimeField(source="class_session.end_time", read_only=True)

    class Meta:
        model = AttendanceQrSession
        fields = (
            "id",
            "course",
            "course_code",
            "course_title",
            "class_session",
            "class_session_start_time",
            "class_session_end_time",
            "created_by",
            "token",
            "date",
            "starts_at",
            "ends_at",
            "is_active",
            "finalized_at",
            "created_at",
        )


class AttendanceQrScanSerializer(serializers.Serializer):
    token = serializers.UUIDField()
