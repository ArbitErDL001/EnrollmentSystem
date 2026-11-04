from students.roles import ROLE_NAMES
from students.models import DirectMessage


def account_roles(request):
    path_parts = request.path.strip('/').split('/')
    active_section = path_parts[0]
    if path_parts[:2] == ['students', 'users']:
        active_section = 'users'
    if not request.user.is_authenticated:
        return {
            'user_roles': [],
            'is_system_admin': False,
            'active_section': active_section,
            'unread_message_count': 0,
        }
    roles = list(request.user.groups.filter(name__in=ROLE_NAMES).values_list('name', flat=True))
    if request.user.is_superuser and 'Admin' not in roles:
        roles.append('Admin')
    return {
        'user_roles': roles,
        'is_system_admin': request.user.is_superuser,
        'active_section': active_section,
        'unread_message_count': DirectMessage.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count(),
    }
