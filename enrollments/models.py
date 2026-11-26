from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Enrollment(models.Model):
    STATUSES = [('enrolled', 'Enrolled'), ('completed', 'Completed'), ('dropped', 'Dropped')]

    student = models.ForeignKey('students.StudentProfile', on_delete=models.PROTECT, related_name='enrollments')
    offering = models.ForeignKey('scheduling.ClassOffering', on_delete=models.PROTECT, related_name='enrollments')
    status = models.CharField(max_length=12, choices=STATUSES, default='enrolled')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-enrolled_at',)
        constraints = [
            models.UniqueConstraint(fields=('student', 'offering'), name='unique_student_offering'),
        ]

    def clean(self):
        if not self.student_id or not self.offering_id:
            return
        entry = self.offering.curriculum_entry
        if self.student.status != 'active':
            raise ValidationError({'student': 'Only active students may enroll.'})
        if not entry.program.is_active or not entry.subject.is_active:
            raise ValidationError({'offering': 'This program or subject is not active for enrollment.'})
        if self.student.program_id != entry.program_id or self.student.year_level != entry.year_level:
            raise ValidationError({'offering': 'This class is not in your assigned program and year-level curriculum.'})
        if not self.offering.is_active:
            raise ValidationError({'offering': 'This class is not open for enrollment.'})
        if self.status == 'enrolled' and self.offering.enrollments.filter(status='enrolled').exclude(pk=self.pk).count() >= self.offering.capacity:
            raise ValidationError({'offering': 'This class section is full.'})
        existing = Enrollment.objects.filter(
            student_id=self.student_id,
            offering__term=self.offering.term,
            status='enrolled',
        ).exclude(pk=self.pk)
        if existing.filter(offering__curriculum_entry__subject_id=entry.subject_id).exists():
            raise ValidationError({'offering': 'You are already enrolled in this subject for the selected term.'})
        if existing.filter(
            offering__start_time__lt=self.offering.end_time,
            offering__end_time__gt=self.offering.start_time,
        ).exists():
            for enrollment in existing.select_related('offering'):
                other = enrollment.offering
                if self.offering.day_codes.intersection(other.day_codes):
                    raise ValidationError({'offering': 'This class conflicts with another enrolled class.'})
        completed_subjects = Enrollment.objects.filter(
            student_id=self.student_id,
            status='completed',
        ).values_list('offering__curriculum_entry__subject_id', flat=True)
        missing = entry.prerequisites.exclude(pk__in=completed_subjects)
        if missing.exists():
            raise ValidationError({
                'offering': 'Complete these prerequisites first: ' + ', '.join(missing.values_list('code', flat=True))
            })

    def __str__(self):
        return f'{self.student.student_id} - {self.offering}'


class EnrollmentRequest(models.Model):
    STATUSES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(
        'students.StudentProfile', on_delete=models.PROTECT, related_name='enrollment_requests'
    )
    offering = models.ForeignKey(
        'scheduling.ClassOffering', on_delete=models.PROTECT, related_name='enrollment_requests'
    )
    status = models.CharField(max_length=10, choices=STATUSES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='decided_enrollment_requests',
    )
    notification_message = models.OneToOneField(
        'students.DirectMessage', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='enrollment_request',
    )

    class Meta:
        ordering = ('-submitted_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'offering'),
                condition=Q(status='pending'),
                name='unique_pending_enrollment_request',
            ),
        ]

    def __str__(self):
        return f'{self.student.student_id} requested {self.offering}'
