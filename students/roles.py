from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ROLE_NAMES = (
    'Admin',
    'Registrar',
    'Cashier',
    'Instructor',
    'Student',
)

STAFF_ROLES = {
    'Admin',
    'Registrar',
    'Cashier',
    'Instructor',
}


def has_role(user, *roles):
    if user.is_superuser:
        return 'Admin' in roles
    return user.groups.filter(name__in=roles).exists()


def roles_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def guarded(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return guarded
    return decorator
