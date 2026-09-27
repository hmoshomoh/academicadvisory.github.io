from . import roles


def role_context(request):
    user = getattr(request, "user", None)
    if user is None:
        return {}
    return {
        "current_role": roles.role_of(user),
        "is_student_role": roles.is_student(user),
        "is_adviser_role": roles.is_adviser(user),
        "is_admin_role": roles.is_admin(user),
    }
