"""GPA/CGPA arithmetic, recommendation rules and adviser scoping."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from academics import recommendations
from academics.models import AcademicRecord, AdvisoryRequest, CourseResult, Recommendation
from accounts import roles
from accounts.models import Adviser, Student
from accounts.tests import make_user


def add_record(student, session, semester, courses):
    record = AcademicRecord.objects.create(
        student=student, session=session, semester=semester
    )
    for code, units, grade in courses:
        CourseResult.objects.create(
            record=record, course_code=code, credit_units=units, grade=grade
        )
    return record


class GpaTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            user=make_user("g1", roles.STUDENT), matric_number="G1"
        )

    def test_gpa_is_credit_weighted(self):
        record = add_record(self.student, "2024/2025", 1, [("A1", 3, "A"), ("B1", 1, "F")])
        # (3*5 + 1*0) / 4 = 3.75 — not the unweighted mean of 2.50.
        self.assertEqual(record.gpa(), Decimal("3.75"))

    def test_cgpa_spans_semesters_and_stays_credit_weighted(self):
        add_record(self.student, "2024/2025", 1, [("A1", 3, "A")])
        add_record(self.student, "2024/2025", 2, [("A2", 1, "C")])
        # (3*5 + 1*3) / 4 = 4.50
        self.assertEqual(recommendations.cgpa_for(self.student), Decimal("4.50"))

    def test_no_records_and_no_courses_return_none_without_dividing_by_zero(self):
        self.assertIsNone(recommendations.cgpa_for(self.student))
        empty = AcademicRecord.objects.create(
            student=self.student, session="2025/2026", semester=1
        )
        self.assertIsNone(empty.gpa())


class RecommendationRuleTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            user=make_user("r1", roles.STUDENT), matric_number="R1"
        )

    def kinds_for(self, courses):
        record = add_record(self.student, "2024/2025", 1, courses)
        return record, {r.kind for r in recommendations.generate_for_record(record)}

    def test_satisfactory_gpa_yields_course_advice(self):
        _, kinds = self.kinds_for([("A1", 3, "A"), ("A2", 3, "B")])
        self.assertEqual(kinds, {Recommendation.COURSE_ADVICE})

    def test_gpa_below_warning_threshold_yields_a_warning(self):
        _, kinds = self.kinds_for([("A1", 3, "C"), ("A2", 3, "E")])  # (9+3)/6 = 2.00
        self.assertEqual(kinds, {Recommendation.WARNING})

    def test_gpa_below_probation_threshold_yields_a_probation_alert(self):
        _, kinds = self.kinds_for([("A1", 3, "F"), ("A2", 3, "E")])  # (0+3)/6 = 0.50
        self.assertEqual(kinds, {Recommendation.PROBATION_ALERT})

    def test_regenerating_does_not_duplicate_and_drops_stale_kinds(self):
        record, _ = self.kinds_for([("A1", 3, "F"), ("A2", 3, "E")])
        self.assertEqual(record.recommendations.count(), 1)
        recommendations.generate_for_record(record)
        self.assertEqual(record.recommendations.count(), 1)
        record.course_results.update(grade="A")
        recommendations.generate_for_record(record)
        self.assertEqual(
            [r.kind for r in record.recommendations.all()], [Recommendation.COURSE_ADVICE]
        )

    def test_recommendation_is_attached_to_its_record(self):
        record, _ = self.kinds_for([("A1", 3, "A")])
        self.assertEqual(record.recommendations.first().record_id, record.pk)


class AdviserScopingTests(TestCase):
    def setUp(self):
        self.adviser = Adviser.objects.create(
            user=make_user("adv1", roles.ADVISER), staff_number="S1"
        )
        other = Adviser.objects.create(
            user=make_user("adv2", roles.ADVISER), staff_number="S2"
        )
        self.mine = Student.objects.create(
            user=make_user("mine", roles.STUDENT), matric_number="MINE", adviser=self.adviser
        )
        self.theirs = Student.objects.create(
            user=make_user("theirs", roles.STUDENT), matric_number="THEIRS", adviser=other
        )
        add_record(self.mine, "2024/2025", 1, [("A1", 3, "A")])
        add_record(self.theirs, "2024/2025", 1, [("A1", 3, "A")])
        self.client.login(username="adv1", password="Testing!2026")

    def test_adviser_sees_only_assigned_students(self):
        response = self.client.get(reverse("academics:adviser_students"))
        self.assertContains(response, "MINE")
        self.assertNotContains(response, "THEIRS")

    def test_unassigned_student_detail_is_not_reachable(self):
        self.assertEqual(
            self.client.get(
                reverse("academics:adviser_student_detail", args=[self.theirs.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("academics:adviser_student_detail", args=[self.mine.pk])
            ).status_code,
            200,
        )

    def test_student_asks_and_adviser_answers(self):
        self.client.login(username="mine", password="Testing!2026")
        self.client.post(
            reverse("academics:advisory_request_create"),
            {"subject": "Overload", "body": "Can I take 24 units?"},
        )
        advisory = AdvisoryRequest.objects.get(student=self.mine)
        self.assertEqual(advisory.adviser, self.adviser)

        self.client.login(username="adv1", password="Testing!2026")
        self.client.post(
            reverse("academics:advisory_respond", args=[advisory.pk]),
            {"response": "Keep it at 21 units."},
        )
        advisory.refresh_from_db()
        self.assertEqual(advisory.response, "Keep it at 21 units.")
        self.assertIsNotNone(advisory.responded_at)

        self.client.login(username="mine", password="Testing!2026")
        self.assertContains(
            self.client.get(reverse("academics:student_overview")), "Keep it at 21 units."
        )
