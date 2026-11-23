from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import DirectMessage


def notify_user(recipient, *, sender, subject, body):
    return DirectMessage.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body,
    )


def notify_role_members(roles, *, sender, subject, body):
    recipients = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=roles)
    ).exclude(pk=sender.pk).distinct()
    return [
        notify_user(recipient, sender=sender, subject=subject, body=body)
        for recipient in recipients
    ]


def notify_new_account(user, role, *, sender, student_profile=None):
    details = [
        f'Account: {user.username}',
        f'Role: {role}',
    ]
    if student_profile:
        details.extend((
            f'Student ID: {student_profile.student_id}',
            f'Program: {student_profile.program or "Not assigned"}',
            f'Year level: {student_profile.year_level}',
        ))
    details.append('Open Students → User management to review the account.')
    return notify_role_members(
        ('Admin',),
        sender=sender,
        subject=f'New account created: {user.username}',
        body='\n'.join(details),
    )
