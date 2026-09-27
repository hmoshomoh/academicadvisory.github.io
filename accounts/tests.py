"""Auth, roles and RBAC. Kept minimal: the claims the gate cannot verify by eye."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts import roles
from accounts.models import Adviser, Student


def make_user(username, role, **extra):
    user = User.objects.create_user(username=username, password="Testing!2026", **extra)
    if role:
        user.groups.add(*[g for g in roles.ensure_groups() if g.name == role])
    return user


class RegistrationTests(TestCase):
    def test_registration_creates_student_in_student_group_with_hashed_password(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newstudent", "first_name": "New", "last_name": "Student",
                "email": "new@example.edu", "matric_number": "csc/2026/099",
                "programme": "B.Sc.", "password1": "Testing!2026", "password2": "Testing!2026",
            },
        )
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)
        user = User.objects.get(username="newstudent")
        self.assertTrue(roles.is_student(user))
        self.assertEqual(user.student.matric_number, "CSC/2026/099")
        self.assertNotEqual(user.password, "Testing!2026")
        self.assertTrue(user.check_password("Testing!2026"))

    def test_login_and_logout(self):
        make_user("s1", roles.STUDENT)
        self.assertTrue(self.client.login(username="s1", password="Testing!2026"))
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class RoleAccessTests(TestCase):
    def setUp(self):
        self.student_user = make_user("stud", roles.STUDENT)
        Student.objects.create(user=self.student_user, matric_number="M1")
        self.adviser_user = make_user("adv", roles.ADVISER)
        Adviser.objects.create(user=self.adviser_user, staff_number="S1")
        make_user("adm", roles.ADMIN)

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(reverse("academics:student_overview"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_student_cannot_reach_adviser_or_admin_views(self):
        self.client.login(username="stud", password="Testing!2026")
        for url in [reverse("academics:adviser_students"), reverse("complaints:admin_list"),
                    reverse("complaints:dashboard"), reverse("complaints:export_csv")]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_adviser_cannot_reach_admin_views_or_complaints(self):
        self.client.login(username="adv", password="Testing!2026")
        for url in [reverse("complaints:admin_list"), reverse("complaints:dashboard"),
                    reverse("complaints:export_csv"), reverse("complaints:submit"),
                    reverse("complaints:my_complaints")]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_each_role_lands_on_its_own_dashboard(self):
        expected = {
            "stud": reverse("academics:student_overview"),
            "adv": reverse("academics:adviser_students"),
            "adm": reverse("complaints:admin_list"),
        }
        for username, target in expected.items():
            self.client.login(username=username, password="Testing!2026")
            self.assertRedirects(
                self.client.get(reverse("accounts:dashboard")), target,
                fetch_redirect_response=False,
            )
