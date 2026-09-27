from django.core.management.base import BaseCommand

from accounts.roles import ensure_groups
from complaints.models import ComplaintCategory

DEFAULT_CATEGORIES = [
    ("Academic", "Grades, results, course registration and examinations."),
    ("Facilities", "Classrooms, laboratories, hostels and equipment."),
    ("Staff conduct", "Conduct of lecturers or administrative staff."),
    ("Finance", "Fees, receipts, scholarships and refunds."),
    ("Other", "Anything that does not fit the categories above."),
]


class Command(BaseCommand):
    help = "Create the Student/Adviser/Admin groups and the default complaint categories."

    def handle(self, *args, **options):
        groups = ensure_groups()
        self.stdout.write("Groups: {}".format(", ".join(g.name for g in groups)))
        for name, description in DEFAULT_CATEGORIES:
            _, created = ComplaintCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            self.stdout.write("{} category: {}".format("created" if created else "present", name))
        self.stdout.write(self.style.SUCCESS("Roles and categories are in place."))
