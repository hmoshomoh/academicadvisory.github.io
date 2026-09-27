from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from accounts.roles import ADMIN, ensure_groups
from complaints.models import ComplaintCategory

DEFAULT_CATEGORIES = [
    ("Academic", "Grades, results, course registration and examinations."),
    ("Facilities", "Classrooms, laboratories, hostels and equipment."),
    ("Staff conduct", "Conduct of lecturers or administrative staff."),
    ("Finance", "Fees, receipts, scholarships and refunds."),
    ("Other", "Anything that does not fit the categories above."),
]


# The Admin group also works Django's own admin site, which is where academic
# records are entered and students are assigned to advisers. The complaint
# workflow itself lives in the app's own views, not here.
ADMIN_MODEL_PERMISSIONS = [
    ("accounts", "student"),
    ("accounts", "adviser"),
    ("academics", "academicrecord"),
    ("academics", "courseresult"),
    ("academics", "recommendation"),
    ("academics", "advisoryrequest"),
    ("complaints", "complaintcategory"),
    ("complaints", "complaint"),
    ("complaints", "complaintstatuslog"),
]


class Command(BaseCommand):
    help = "Create the Student/Adviser/Admin groups and the default complaint categories."

    def handle(self, *args, **options):
        groups = ensure_groups()
        self.stdout.write("Groups: {}".format(", ".join(g.name for g in groups)))

        admin_group = next(g for g in groups if g.name == ADMIN)
        permissions = Permission.objects.filter(
            content_type__app_label__in={app for app, _ in ADMIN_MODEL_PERMISSIONS},
            content_type__model__in={model for _, model in ADMIN_MODEL_PERMISSIONS},
        )
        admin_group.permissions.set(permissions)
        self.stdout.write("Admin group: {} model permissions".format(permissions.count()))
        for name, description in DEFAULT_CATEGORIES:
            _, created = ComplaintCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            self.stdout.write("{} category: {}".format("created" if created else "present", name))
        self.stdout.write(self.style.SUCCESS("Roles and categories are in place."))
