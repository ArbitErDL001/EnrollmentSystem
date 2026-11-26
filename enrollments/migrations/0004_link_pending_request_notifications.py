from django.db import migrations


def link_existing_pending_notifications(apps, schema_editor):
    EnrollmentRequest = apps.get_model('enrollments', 'EnrollmentRequest')
    DirectMessage = apps.get_model('students', 'DirectMessage')
    database = schema_editor.connection.alias
    linked_message_ids = set(
        EnrollmentRequest.objects.using(database)
        .exclude(notification_message_id=None)
        .values_list('notification_message_id', flat=True)
    )

    pending_requests = EnrollmentRequest.objects.using(database).filter(
        status='pending',
        notification_message_id=None,
    ).select_related(
        'student__user',
        'offering__instructor',
        'offering__curriculum_entry__subject',
    )
    for enrollment_request in pending_requests.iterator():
        student = enrollment_request.student
        offering = enrollment_request.offering
        subject = offering.curriculum_entry.subject
        student_name = (
            f'{student.user.first_name} {student.user.last_name}'.strip()
            or student.user.username
        )
        message_body = (
            f'{student_name} '
            f'({student.student_id}) requested {subject.code}, section '
            f'{offering.section}, for {offering.term}.\n'
            'Open Enrollments → Enrollment requests to review it.'
        )
        candidates = list(
            DirectMessage.objects.using(database).filter(
                sender_id=student.user_id,
                recipient_id=offering.instructor_id,
                subject=f'Enrollment request: {subject.code} {offering.section}',
                body=message_body,
            ).exclude(pk__in=linked_message_ids)
        )
        if not candidates:
            continue
        notification = min(
            candidates,
            key=lambda message: abs(message.created_at - enrollment_request.submitted_at),
        )
        enrollment_request.notification_message_id = notification.pk
        enrollment_request.save(using=database, update_fields=('notification_message',))
        linked_message_ids.add(notification.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0003_enrollmentrequest_notification_message'),
    ]

    operations = [
        migrations.RunPython(
            link_existing_pending_notifications,
            migrations.RunPython.noop,
        ),
    ]
