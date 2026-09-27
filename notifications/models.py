from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(recipient=user)

    def unread(self):
        return self.filter(read_at__isnull=True)


class Notification(models.Model):
    """A status-change notice.

    `recipient` is NULL when the complaint was anonymous: there is no student to
    address it to, and inventing one would re-link the identity we refused to
    store. Those notices are delivered by the tracking page instead.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    complaint = models.ForeignKey(
        "complaints.Complaint",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    message = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message

    @property
    def unread(self):
        return self.read_at is None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
