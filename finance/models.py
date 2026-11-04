import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class FeePolicy(models.Model):
    tuition_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=1000, validators=[MinValueValidator(0)])
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500, validators=[MinValueValidator(0)])
    technology_fee = models.DecimalField(max_digits=10, decimal_places=2, default=250, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Fee policy (updated {self.updated_at:%Y-%m-%d})'


class Assessment(models.Model):
    student = models.ForeignKey('students.StudentProfile', on_delete=models.PROTECT, related_name='assessments')
    term = models.CharField(max_length=30)
    units = models.PositiveSmallIntegerField(default=0)
    tuition_per_unit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tuition = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    technology_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(fields=('student', 'term'), name='unique_student_term_assessment'),
        ]

    @property
    def total(self):
        return self.tuition + self.registration_fee + self.technology_fee

    @property
    def paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def balance(self):
        return self.total - self.paid

    def __str__(self):
        return f'Assessment {self.student.student_id} - {self.term}'


def new_payment_reference():
    return f'PAY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'


class Payment(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name='payments')
    reference = models.CharField(max_length=30, unique=True, default=new_payment_reference, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    received_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='recorded_payments'
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ('-received_at',)

    def __str__(self):
        return f'{self.reference}: {self.amount}'
