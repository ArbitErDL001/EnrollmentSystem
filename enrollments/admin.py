from django.contrib import admin

from .models import Enrollment, EnrollmentRequest


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'offering', 'status', 'enrolled_at')
    list_filter = ('status', 'offering__term', 'offering__curriculum_entry__program')
    search_fields = ('student__student_id', 'student__user__username', 'offering__curriculum_entry__subject__code')


@admin.register(EnrollmentRequest)
class EnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'offering', 'status', 'submitted_at', 'decided_by', 'decided_at')
    list_filter = ('status', 'offering__term', 'offering__curriculum_entry__program')
    search_fields = ('student__student_id', 'student__user__username', 'offering__curriculum_entry__subject__code')
