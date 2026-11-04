from django.db import transaction

from .models import Assessment, FeePolicy


@transaction.atomic
def refresh_assessment(student, term):
    policy, _ = FeePolicy.objects.get_or_create(
        pk=1,
        defaults={
            'tuition_per_unit': 1000,
            'registration_fee': 500,
            'technology_fee': 250,
        },
    )
    units = sum(
        enrollment.offering.curriculum_entry.subject.units
        for enrollment in student.enrollments.filter(
            status='enrolled',
            offering__term=term,
        ).select_related('offering__curriculum_entry__subject')
    )
    assessment, created = Assessment.objects.get_or_create(
        student=student,
        term=term,
        defaults={
            'tuition_per_unit': policy.tuition_per_unit,
            'registration_fee': policy.registration_fee,
            'technology_fee': policy.technology_fee,
        },
    )
    assessment.units = units
    assessment.tuition = units * assessment.tuition_per_unit
    fields = ['units', 'tuition']
    if created:
        fields.extend(('tuition_per_unit', 'registration_fee', 'technology_fee'))
    assessment.save(update_fields=fields)
    return assessment
