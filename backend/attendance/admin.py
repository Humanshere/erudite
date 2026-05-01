from django.contrib import admin

from .models import AttendanceQrSession, AttendanceRecord

admin.site.register(AttendanceRecord)
admin.site.register(AttendanceQrSession)
