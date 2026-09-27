from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import Student

from . import references
from .validators import validate_attachment


class ComplaintStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under review"
    ESCALATED = "escalated", "Escalated"
    RESOLVED = "resolved", "Resolved"


OPEN_STATUSES = [
    ComplaintStatus.SUBMITTED,
    ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.ESCALATED,
]


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = "complaint categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ComplaintQuerySet(models.QuerySet):
    def named(self):
        return self.filter(is_anonymous=False)

    def anonymous(self):
        return self.filter(is_anonymous=True)

    def for_student(self, student):
        """A student's own complaints.

        Anonymous complaints are unreachable here by construction: they hold no
        student id at all, so there is nothing for this filter to match.
        """
        return self.named().filter(student=student)


class Complaint(models.Model):
    """A complaint, named or anonymous.

    Anonymity design: an anonymous complaint stores **no** submitter identity —
    not a nulled-out FK to a row we kept elsewhere, not a hash, not an audit
    column. `student_id` is NULL and there is no side table mapping references to
    students, so no query, join or export can re-link it. The `anonymous_has_no_student`
    database constraint makes the leak unrepresentable rather than merely avoided.
    The reference is the only link back, and it lives with the submitter, outside
    this database.
    """

    reference = models.CharField(max_length=24, unique=True, editable=False)
    is_anonymous = models.BooleanField(default=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="complaints",
        help_text="Always NULL for an anonymous complaint.",
    )
    category = models.ForeignKey(
        ComplaintCategory, on_delete=models.PROTECT, related_name="complaints"
    )
    subject = models.CharField(max_length=160)
    body = models.TextField()
    attachment = models.FileField(
        upload_to="complaints/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_attachment],
    )
    status = models.CharField(
        max_length=16, choices=ComplaintStatus.choices, default=ComplaintStatus.SUBMITTED
    )
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = ComplaintQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(is_anonymous=False) | models.Q(student__isnull=True),
                name="anonymous_has_no_student",
            ),
            models.CheckConstraint(
                check=models.Q(is_anonymous=True) | models.Q(student__isnull=False),
                name="named_complaint_has_a_student",
            ),
        ]

    def __str__(self):
        return "{} — {}".format(self.reference, self.subject)

    def save(self, *args, **kwargs):
        if self.is_anonymous and self.student_id is not None:
            raise ValidationError("An anonymous complaint cannot carry a student.")
        if not self.reference:
            self.reference = self._unique_reference()
        return super().save(*args, **kwargs)

    @staticmethod
    def _unique_reference():
        for _ in range(10):
            candidate = references.new_reference()
            if not Complaint.objects.filter(reference=candidate).exists():
                return candidate
        raise RuntimeError("Could not allocate a unique complaint reference.")

    @property
    def submitter_label(self):
        """What any viewer — admin included — is allowed to see as the submitter."""
        if self.is_anonymous:
            return "Anonymous"
        return self.student.display_name if self.student else "Unknown"

    @property
    def is_resolved(self):
        return self.status == ComplaintStatus.RESOLVED

    @property
    def status_css(self):
        return {
            ComplaintStatus.SUBMITTED: "secondary",
            ComplaintStatus.UNDER_REVIEW: "info",
            ComplaintStatus.ESCALATED: "warning",
            ComplaintStatus.RESOLVED: "success",
        }.get(self.status, "secondary")

    def resolution_hours(self):
        if not (self.is_resolved and self.resolved_at):
            return None
        return (self.resolved_at - self.created_at).total_seconds() / 3600.0


class ComplaintStatusLog(models.Model):
    """Append-only audit trail: who did what, when, on a complaint.

    Append-only is enforced in `save`/`delete` rather than by convention, so no
    view, form or admin action can rewrite history.
    """

    SUBMITTED = "submitted"
    CATEGORISED = "categorised"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    REVIEWED = "reviewed"
    ACTIONS = [
        (SUBMITTED, "Submitted"),
        (CATEGORISED, "Re-categorised"),
        (REVIEWED, "Moved to review"),
        (ESCALATED, "Escalated"),
        (RESOLVED, "Resolved"),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="status_logs"
    )
    action = models.CharField(max_length=16, choices=ACTIONS)
    from_status = models.CharField(
        max_length=16, choices=ComplaintStatus.choices, blank=True
    )
    to_status = models.CharField(max_length=16, choices=ComplaintStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_actions",
        help_text="NULL when the action had no identifiable actor to record.",
    )
    actor_label = models.CharField(
        max_length=80,
        help_text="Frozen display name, so the trail survives a user rename.",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "complaint status log entry"
        verbose_name_plural = "complaint status log"

    def __str__(self):
        return "{} {} -> {}".format(self.complaint.reference, self.action, self.to_status)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("The complaint status log is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("The complaint status log is append-only.")
