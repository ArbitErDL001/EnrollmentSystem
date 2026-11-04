import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def new_student_id():
    return f'STU-{timezone.now():%Y}-{uuid.uuid4().hex[:8].upper()}'


class StudentProfile(models.Model):
    YEAR_LEVELS = [(year, f'Year {year}') for year in range(1, 7)]
    STATUSES = [('active', 'Active'), ('inactive', 'Inactive'), ('graduated', 'Graduated')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True, default=new_student_id, editable=False)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    program = models.ForeignKey('academics.Program', null=True, blank=True, on_delete=models.PROTECT, related_name='students')
    year_level = models.PositiveSmallIntegerField(choices=YEAR_LEVELS, default=1)
    status = models.CharField(max_length=12, choices=STATUSES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('student_id',)

    def __str__(self):
        return f'{self.student_id} - {self.user.get_full_name() or self.user.username}'


class DirectMessage(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_direct_messages',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_direct_messages',
    )
    subject = models.CharField(max_length=150)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.subject
