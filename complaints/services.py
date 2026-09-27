"""The only write path for complaints.

Every status change goes through `record_status_change`, so the append-only log
and the notification are impossible to forget, and the anonymity rule is applied
in one place instead of at every call site.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from notifications.models import Notification

from .models import Complaint, ComplaintStatus, ComplaintStatusLog

SYSTEM_ACTOR_LABEL = "System"
ANONYMOUS_SUBMITTER_LABEL = "Anonymous submitter"


@transaction.atomic
def submit_complaint(*, category, subject, body, attachment=None, student=None, anonymous=False):
    """Create a complaint and its opening log row.

    An anonymous submission is stored with no student at all, and its log row
    names no actor — the submitter's identity never enters the database.
    """
    if not anonymous and student is None:
        raise ValidationError("A named complaint needs a student.")
    complaint = Complaint.objects.create(
        is_anonymous=anonymous,
        student=None if anonymous else student,
        category=category,
        subject=subject,
        body=body,
        attachment=attachment,
        status=ComplaintStatus.SUBMITTED,
    )
    ComplaintStatusLog.objects.create(
        complaint=complaint,
        action=ComplaintStatusLog.SUBMITTED,
        from_status="",
        to_status=ComplaintStatus.SUBMITTED,
        actor=None if anonymous else student.user,
        actor_label=ANONYMOUS_SUBMITTER_LABEL if anonymous else student.display_name,
        note="Complaint submitted.",
    )
    return complaint


@transaction.atomic
def record_status_change(*, complaint, actor, action, to_status, note=""):
    """Append a log row, move the complaint, and notify. The only mutator."""
    if to_status not in ComplaintStatus.values:
        raise ValidationError("Unknown complaint status: {}".format(to_status))
    from_status = complaint.status
    complaint.status = to_status
    if to_status == ComplaintStatus.RESOLVED:
        complaint.resolved_at = complaint.resolved_at or timezone.now()
        if note:
            complaint.resolution_note = note
    else:
        complaint.resolved_at = None
    complaint.save(update_fields=["status", "resolved_at", "resolution_note", "updated_at"])

    ComplaintStatusLog.objects.create(
        complaint=complaint,
        action=action,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        actor_label=_actor_label(actor),
        note=note,
    )
    _notify(complaint, to_status)
    return complaint


@transaction.atomic
def recategorise(*, complaint, actor, category, note=""):
    """Change a complaint's category. Logged like any other admin action."""
    previous = complaint.category
    complaint.category = category
    complaint.save(update_fields=["category", "updated_at"])
    detail = "Category changed from {} to {}.".format(previous.name, category.name)
    ComplaintStatusLog.objects.create(
        complaint=complaint,
        action=ComplaintStatusLog.CATEGORISED,
        from_status=complaint.status,
        to_status=complaint.status,
        actor=actor,
        actor_label=_actor_label(actor),
        note="{} {}".format(detail, note).strip(),
    )
    _notify(complaint, complaint.status, headline="Complaint re-categorised")
    return complaint


def _actor_label(actor):
    if actor is None:
        return SYSTEM_ACTOR_LABEL
    return actor.get_full_name() or actor.get_username()


def _notify(complaint, status, headline=None):
    """One notification per change.

    For an anonymous complaint the notice has no recipient: there is no student
    on the record to address, by design. It is read through the tracking page.
    """
    label = headline or "Complaint is now {}".format(ComplaintStatus(status).label.lower())
    message = "{} ({})".format(label, complaint.reference)
    recipient = None
    if not complaint.is_anonymous and complaint.student_id:
        recipient = complaint.student.user
    return Notification.objects.create(
        recipient=recipient, complaint=complaint, message=message[:240]
    )
