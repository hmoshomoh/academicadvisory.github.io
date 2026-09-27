"""The three roles, expressed as Django auth Groups."""

from django.contrib.auth.models import Group

STUDENT = "Student"
ADVISER = "Adviser"
ADMIN = "Admin"

ALL_ROLES = (STUDENT, ADVISER, ADMIN)


def ensure_groups():
    """Create the three role groups. Idempotent, so it is safe to re-run."""
    return [Group.objects.get_or_create(name=name)[0] for name in ALL_ROLES]


def in_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()


def is_student(user):
    return in_group(user, STUDENT)


def is_adviser(user):
    return in_group(user, ADVISER)


def is_admin(user):
    return in_group(user, ADMIN) or (user.is_authenticated and user.is_superuser)


def role_of(user):
    """The single role used for routing. Admin wins, then adviser, then student."""
    if is_admin(user):
        return ADMIN
    if is_adviser(user):
        return ADVISER
    if is_student(user):
        return STUDENT
    return None
