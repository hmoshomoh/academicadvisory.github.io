"""View-level RBAC. One decorator per role, built on user_passes_test."""

from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied

from . import roles


def _role_required(test):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not test(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


student_required = _role_required(roles.is_student)
adviser_required = _role_required(roles.is_adviser)
admin_required = _role_required(roles.is_admin)

__all__ = [
    "student_required",
    "adviser_required",
    "admin_required",
    "login_required",
    "user_passes_test",
]
