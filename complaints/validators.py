from django.conf import settings
from django.core.exceptions import ValidationError


def validate_attachment(uploaded):
    """Reject oversized or unexpected uploads as a form error, never as a 500."""
    name = getattr(uploaded, "name", "") or ""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    allowed = settings.COMPLAINT_ATTACHMENT_EXTENSIONS
    if extension not in allowed:
        raise ValidationError(
            "Attachments must be one of: %(allowed)s.",
            params={"allowed": ", ".join(allowed)},
        )
    limit = settings.COMPLAINT_ATTACHMENT_MAX_BYTES
    if uploaded.size > limit:
        raise ValidationError(
            "Attachment is larger than %(mb)sMB.",
            params={"mb": limit // (1024 * 1024)},
        )
