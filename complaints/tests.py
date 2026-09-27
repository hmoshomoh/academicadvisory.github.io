"""Complaints: the anonymity guarantee, tracking, admin workflow, audit log, export."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse

from accounts import roles
from accounts.models import Adviser, Student
from accounts.tests import make_user
from complaints import services
from complaints.models import (
    Complaint,
    ComplaintCategory,
    ComplaintStatus,
    ComplaintStatusLog,
)
from notifications.models import Notification


class ComplaintTestCase(TestCase):
    def setUp(self):
        self.category = ComplaintCategory.objects.create(name="Academic")
        self.other_category = ComplaintCategory.objects.create(name="Facilities")
        self.student = Student.objects.create(
            user=make_user("stu", roles.STUDENT, first_name="Ada", last_name="Eze"),
            matric_number="CSC/001",
        )
        self.admin_user = make_user("adm", roles.ADMIN, first_name="Sam", last_name="Admin")

    def login_student(self):
        self.client.login(username="stu", password="Testing!2026")

    def login_admin(self):
        self.client.login(username="adm", password="Testing!2026")

    def submit(self, anonymous, **extra):
        self.login_student()
        payload = {
            "category": self.category.pk,
            "subject": "Missing result",
            "body": "My CSC201 result is missing.",
        }
        if anonymous:
            payload["submit_anonymously"] = "on"
        payload.update(extra)
        return self.client.post(reverse("complaints:submit"), payload, follow=True)


class SubmissionTests(ComplaintTestCase):
    def test_named_submission_is_linked_and_returns_a_reference(self):
        response = self.submit(anonymous=False)
        complaint = Complaint.objects.get()
        self.assertFalse(complaint.is_anonymous)
        self.assertEqual(complaint.student, self.student)
        self.assertContains(response, complaint.reference)

    def test_references_are_unique_and_not_sequential(self):
        for _ in range(5):
            self.submit(anonymous=False)
        references = list(Complaint.objects.values_list("reference", flat=True))
        self.assertEqual(len(set(references)), 5)
        suffixes = [r.split("-")[1] for r in references]
        self.assertFalse(any(s.isdigit() and int(s) in (1, 2, 3, 4, 5) for s in suffixes))
        for reference in references:
            self.assertNotIn(str(self.student.pk), reference.split("-")[1])

    def test_attachment_is_stored_and_retrievable(self):
        upload = SimpleUploadedFile("evidence.txt", b"proof", content_type="text/plain")
        self.submit(anonymous=False, attachment=upload)
        complaint = Complaint.objects.get()
        self.assertTrue(complaint.attachment)
        with complaint.attachment.open("rb") as handle:
            self.assertEqual(handle.read(), b"proof")
        complaint.attachment.delete(save=False)

    def test_junk_upload_is_a_form_error_not_a_crash(self):
        upload = SimpleUploadedFile("payload.exe", b"MZ", content_type="application/x-msdownload")
        response = self.submit(anonymous=False, attachment=upload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertContains(response, "Attachments must be one of")


class AnonymityTests(ComplaintTestCase):
    def test_anonymous_complaint_stores_no_identity_at_the_database_level(self):
        self.submit(anonymous=True)
        complaint = Complaint.objects.get()
        self.assertTrue(complaint.is_anonymous)
        self.assertIsNone(complaint.student_id)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT student_id FROM complaints_complaint WHERE reference = %s",
                [complaint.reference],
            )
            self.assertEqual(cursor.fetchone(), (None,))

    def test_no_column_anywhere_can_rejoin_an_anonymous_complaint_to_a_student(self):
        """Nothing outside `student_id` references a student, so there is no join back."""
        self.submit(anonymous=True)
        complaint = Complaint.objects.get()
        columns = [f.name for f in Complaint._meta.get_fields() if hasattr(f, "attname")]
        self.assertEqual(
            [c for c in columns if "student" in c or "user" in c], ["student"]
        )
        self.assertFalse(Complaint.objects.for_student(self.student).exists())
        self.assertFalse(self.student.complaints.exists())
        for log in complaint.status_logs.all():
            self.assertIsNone(log.actor_id)
            self.assertNotIn("Ada", log.actor_label)
            self.assertNotIn(self.student.matric_number, log.actor_label)

    def test_both_the_model_and_the_database_refuse_an_identified_anonymous_complaint(self):
        with self.assertRaises(ValidationError):
            Complaint.objects.create(
                is_anonymous=True, student=self.student, category=self.category,
                subject="x", body="y",
            )
        # And the same leak is rejected by the CHECK constraint when `save` is bypassed,
        # so no raw update, data migration or shell session can create one either.
        self.submit(anonymous=False)
        named = Complaint.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Complaint.objects.filter(pk=named.pk).update(is_anonymous=True)

    def test_admin_sees_anonymous_label_for_anonymous_and_a_name_for_named(self):
        self.submit(anonymous=True)
        anonymous = Complaint.objects.get()
        self.submit(anonymous=False)
        named = Complaint.objects.exclude(pk=anonymous.pk).get()

        self.login_admin()
        anonymous_page = self.client.get(reverse("complaints:admin_detail", args=[anonymous.pk]))
        self.assertContains(anonymous_page, "Anonymous")
        self.assertNotContains(anonymous_page, "Ada")
        self.assertNotContains(anonymous_page, self.student.matric_number)

        named_page = self.client.get(reverse("complaints:admin_detail", args=[named.pk]))
        self.assertContains(named_page, "Ada")
        self.assertContains(named_page, self.student.matric_number)

    def test_anonymous_complaint_never_appears_in_a_student_list(self):
        self.submit(anonymous=True)
        response = self.client.get(reverse("complaints:my_complaints"))
        self.assertNotContains(response, Complaint.objects.get().reference)

    def test_adviser_cannot_reach_any_complaint_view(self):
        self.submit(anonymous=False)
        complaint = Complaint.objects.get()
        Adviser.objects.create(user=make_user("adv", roles.ADVISER), staff_number="S9")
        self.client.login(username="adv", password="Testing!2026")
        for url in [reverse("complaints:admin_list"),
                    reverse("complaints:admin_detail", args=[complaint.pk]),
                    reverse("complaints:my_complaint_detail", args=[complaint.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403, url)


class TrackingTests(ComplaintTestCase):
    def test_reference_holder_sees_status_without_logging_in_and_no_identity(self):
        self.submit(anonymous=True)
        complaint = Complaint.objects.get()
        self.client.logout()
        response = self.client.get(
            reverse("complaints:track"), {"reference": complaint.reference.lower()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submitted")
        self.assertNotContains(response, "Ada")
        self.assertNotContains(response, self.student.matric_number)

    def test_named_complaint_tracking_page_also_hides_identity(self):
        self.submit(anonymous=False)
        complaint = Complaint.objects.get()
        self.client.logout()
        response = self.client.get(reverse("complaints:track"), {"reference": complaint.reference})
        self.assertNotContains(response, self.student.matric_number)

    def test_unknown_reference_reports_nothing_found(self):
        self.client.logout()
        response = self.client.get(reverse("complaints:track"), {"reference": "ACS-0000000000"})
        self.assertContains(response, "No complaint matches")


class AdminWorkflowTests(ComplaintTestCase):
    def setUp(self):
        super().setUp()
        self.submit(anonymous=False)
        self.complaint = Complaint.objects.get()
        self.login_admin()

    def act(self, action, **payload):
        # Each admin form is rendered with a prefix so the four `note` fields get
        # distinct element ids, so the POST keys carry that prefix too.
        return self.client.post(
            reverse("complaints:admin_action", args=[self.complaint.pk, action]),
            {"{}-{}".format(action, key): value for key, value in payload.items()},
            follow=True,
        )

    def test_categorise_resolve_and_escalate_each_append_a_log_row(self):
        before = self.complaint.status_logs.count()
        self.act("categorise", category=self.other_category.pk, note="wrong queue")
        self.act("escalate", note="needs the dean")
        self.act("resolve", note="result uploaded")
        self.complaint.refresh_from_db()

        self.assertEqual(self.complaint.category, self.other_category)
        self.assertEqual(self.complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(self.complaint.resolution_note, "result uploaded")
        logs = list(self.complaint.status_logs.all())
        self.assertEqual(len(logs), before + 3)
        self.assertEqual(
            [log.action for log in logs[-3:]],
            [ComplaintStatusLog.CATEGORISED, ComplaintStatusLog.ESCALATED,
             ComplaintStatusLog.RESOLVED],
        )
        for log in logs[-3:]:
            self.assertEqual(log.actor, self.admin_user)
            self.assertEqual(log.actor_label, "Sam Admin")
            self.assertIsNotNone(log.created_at)

    def test_current_status_matches_the_latest_log_row(self):
        self.act("escalate", note="up")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, self.complaint.status_logs.last().to_status)

    def test_log_is_append_only(self):
        log = self.complaint.status_logs.first()
        log.note = "rewritten"
        with self.assertRaises(ValidationError):
            log.save()
        with self.assertRaises(ValidationError):
            log.delete()
        log.refresh_from_db()
        self.assertEqual(log.note, "Complaint submitted.")

    def test_unknown_status_is_refused(self):
        with self.assertRaises(ValidationError):
            services.record_status_change(
                complaint=self.complaint, actor=self.admin_user,
                action=ComplaintStatusLog.REVIEWED, to_status="deleted",
            )

    def test_student_cannot_perform_an_admin_action(self):
        self.login_student()
        self.assertEqual(
            self.client.post(
                reverse("complaints:admin_action", args=[self.complaint.pk, "resolve"]),
                {"resolve-note": "self-serve"},
            ).status_code,
            403,
        )
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, ComplaintStatus.SUBMITTED)


class NotificationTests(ComplaintTestCase):
    def test_named_status_change_notifies_the_submitter(self):
        self.submit(anonymous=False)
        complaint = Complaint.objects.get()
        services.record_status_change(
            complaint=complaint, actor=self.admin_user,
            action=ComplaintStatusLog.RESOLVED, to_status=ComplaintStatus.RESOLVED,
            note="done",
        )
        notification = Notification.objects.get(complaint=complaint)
        self.assertEqual(notification.recipient, self.student.user)

        self.login_student()
        inbox = self.client.get(reverse("notifications:inbox"))
        self.assertContains(inbox, complaint.reference)
        self.client.post(reverse("notifications:mark_read", args=[notification.pk]))
        notification.refresh_from_db()
        self.assertFalse(notification.unread)
        self.assertEqual(Notification.objects.for_user(self.student.user).unread().count(), 0)

    def test_anonymous_status_change_notifies_nobody(self):
        self.submit(anonymous=True)
        complaint = Complaint.objects.get()
        services.record_status_change(
            complaint=complaint, actor=self.admin_user,
            action=ComplaintStatusLog.ESCALATED, to_status=ComplaintStatus.ESCALATED,
        )
        notification = Notification.objects.get(complaint=complaint)
        self.assertIsNone(notification.recipient_id)
        self.assertEqual(Notification.objects.for_user(self.student.user).count(), 0)

    def test_a_user_cannot_read_another_users_notification(self):
        self.submit(anonymous=False)
        complaint = Complaint.objects.get()
        services.record_status_change(
            complaint=complaint, actor=self.admin_user,
            action=ComplaintStatusLog.REVIEWED, to_status=ComplaintStatus.UNDER_REVIEW,
        )
        notification = Notification.objects.get(complaint=complaint)
        self.login_admin()
        self.assertEqual(
            self.client.post(
                reverse("notifications:mark_read", args=[notification.pk])
            ).status_code,
            404,
        )


class DashboardAndExportTests(ComplaintTestCase):
    def test_dashboard_renders_with_no_complaints(self):
        self.login_admin()
        response = self.client.get(reverse("complaints:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total complaints")

    def test_dashboard_counts_volume_categories_statuses_and_resolution_time(self):
        self.submit(anonymous=False)
        self.submit(anonymous=True)
        resolved = Complaint.objects.filter(is_anonymous=False).get()
        services.record_status_change(
            complaint=resolved, actor=self.admin_user,
            action=ComplaintStatusLog.RESOLVED, to_status=ComplaintStatus.RESOLVED, note="fixed",
        )
        self.login_admin()
        response = self.client.get(reverse("complaints:dashboard"))
        self.assertEqual(response.context["total"], 2)
        self.assertEqual(response.context["anonymous_count"], 1)
        self.assertEqual(response.context["resolved_count"], 1)
        self.assertIsNotNone(response.context["average_hours"])
        by_category = {c.name: c.total for c in response.context["by_category"]}
        self.assertEqual(by_category["Academic"], 2)
        by_status = {row["value"]: row["total"] for row in response.context["by_status"]}
        self.assertEqual(by_status[ComplaintStatus.RESOLVED], 1)
        self.assertEqual(by_status[ComplaintStatus.SUBMITTED], 1)

    def test_export_has_no_identity_for_anonymous_rows(self):
        self.submit(anonymous=True)
        self.submit(anonymous=False)
        self.login_admin()
        body = self.client.get(reverse("complaints:export_csv")).content.decode()
        anonymous_reference = Complaint.objects.anonymous().get().reference
        anonymous_row = [line for line in body.splitlines() if anonymous_reference in line][0]
        self.assertIn("Anonymous", anonymous_row)
        self.assertNotIn("Ada", anonymous_row)
        self.assertNotIn(self.student.matric_number, anonymous_row)
        named_reference = Complaint.objects.named().get().reference
        named_row = [line for line in body.splitlines() if named_reference in line][0]
        self.assertIn("Ada", named_row)
