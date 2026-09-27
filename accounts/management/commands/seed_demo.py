"""Reproducible demo data for the manual click-through walkthroughs."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from academics import recommendations
from academics.models import AcademicRecord, AdvisoryRequest, CourseResult
from accounts import roles
from accounts.models import Adviser, Student
from complaints.models import ComplaintCategory
from complaints.services import submit_complaint

PASSWORD = "Walkthrough!2026"

# (matric, first, last, [(session, semester, [(code, title, units, grade)])])
STUDENTS = [
    ("CSC/2022/001", "Ada", "Eze", [
        ("2024/2025", 1, [("CSC201", "Data structures", 3, "A"), ("MTH201", "Linear algebra", 3, "B"),
                          ("GST201", "Peace studies", 2, "A")]),
        ("2024/2025", 2, [("CSC202", "Algorithms", 3, "A"), ("CSC204", "Operating systems", 3, "A"),
                          ("MTH202", "Statistics", 2, "B")]),
    ]),
    ("CSC/2022/002", "Bala", "Musa", [
        ("2024/2025", 1, [("CSC201", "Data structures", 3, "C"), ("MTH201", "Linear algebra", 3, "D"),
                          ("GST201", "Peace studies", 2, "D")]),
    ]),
    ("CSC/2022/003", "Chidi", "Okon", [
        ("2024/2025", 1, [("CSC201", "Data structures", 3, "F"), ("MTH201", "Linear algebra", 3, "E"),
                          ("GST201", "Peace studies", 2, "D")]),
    ]),
]


class Command(BaseCommand):
    help = "Seed advisers, students, results, recommendations and sample complaints."

    @transaction.atomic
    def handle(self, *args, **options):
        student_group, adviser_group, admin_group = roles.ensure_groups()
        if not ComplaintCategory.objects.exists():
            self.stderr.write("Run bootstrap_roles first — no complaint categories exist.")
            return

        adviser = self._adviser("adviser1", "Grace", "Nwosu", "STF/1001", adviser_group)
        self._admin("admin1", "Sam", "Adeyemi", admin_group)

        for matric, first, last, semesters in STUDENTS:
            student = self._student(matric, first, last, adviser, student_group)
            for session, semester, courses in semesters:
                record, _ = AcademicRecord.objects.get_or_create(
                    student=student, session=session, semester=semester
                )
                for code, title, units, grade in courses:
                    CourseResult.objects.update_or_create(
                        record=record,
                        course_code=code,
                        defaults={"course_title": title, "credit_units": units, "grade": grade},
                    )
                recommendations.generate_for_record(record)
            self.stdout.write("{}: CGPA {}".format(matric, recommendations.cgpa_for(student)))

        first_student = Student.objects.get(matric_number=STUDENTS[0][0])
        AdvisoryRequest.objects.get_or_create(
            student=first_student,
            adviser=adviser,
            subject="Course load for next semester",
            defaults={"body": "Should I add an extra elective next semester?"},
        )

        academic = ComplaintCategory.objects.get(name="Academic")
        facilities = ComplaintCategory.objects.get(name="Facilities")
        if not first_student.complaints.exists():
            named = submit_complaint(
                category=academic, subject="Missing result for CSC201",
                body="My CSC201 result is not showing on my record.",
                student=first_student, anonymous=False,
            )
            self.stdout.write("named complaint: {}".format(named.reference))
        anonymous = submit_complaint(
            category=facilities, subject="Laboratory has no working sockets",
            body="None of the sockets in lab 2 work, so we cannot run practicals.",
            student=first_student, anonymous=True,
        )
        self.stdout.write("anonymous complaint: {}".format(anonymous.reference))
        self.stdout.write(self.style.SUCCESS(
            "Seeded. Log in as admin1 / adviser1 / {} with password {}".format(
                STUDENTS[0][0], PASSWORD)
        ))

    def _user(self, username, first, last, group):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": first, "last_name": last,
                      "email": "{}@example.edu".format(username)},
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
        user.groups.add(group)
        return user

    def _adviser(self, username, first, last, staff_number, group):
        user = self._user(username, first, last, group)
        adviser, _ = Adviser.objects.get_or_create(
            user=user, defaults={"staff_number": staff_number, "department": "Computer Science"}
        )
        return adviser

    def _admin(self, username, first, last, group):
        user = self._user(username, first, last, group)
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        return user

    def _student(self, matric, first, last, adviser, group):
        user = self._user(matric.replace("/", "").lower(), first, last, group)
        student, _ = Student.objects.get_or_create(
            user=user,
            defaults={"matric_number": matric, "programme": "B.Sc. Computer Science",
                      "adviser": adviser},
        )
        return student
