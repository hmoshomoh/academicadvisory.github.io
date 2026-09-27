from .models import Notification


def unread_notifications(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"unread_notification_count": 0}
    return {
        "unread_notification_count": Notification.objects.for_user(user).unread().count()
    }
