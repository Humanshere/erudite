from django.contrib import admin

from .models import Course, Department, Enrollment, Semester

admin.site.register(Department)
admin.site.register(Semester)
admin.site.register(Course)
admin.site.register(Enrollment)
