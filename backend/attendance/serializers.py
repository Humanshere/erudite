from rest_framework import serializers

from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            "id",
            "course",
            "course_code",
            "course_title",
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
    records = BulkAttendanceMarkItemSerializer(many=True)
