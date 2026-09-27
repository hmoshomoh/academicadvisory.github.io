from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def inbox(request):
    """A user's own notifications. Scoped by recipient, so no cross-user reads."""
    return render(
        request,
        "notifications/inbox.html",
        {"notifications": Notification.objects.for_user(request.user)[:100]},
    )


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification.objects.for_user(request.user), pk=pk)
    notification.mark_read()
    return redirect("notifications:inbox")


@login_required
def mark_all_read(request):
    for notification in Notification.objects.for_user(request.user).unread():
        notification.mark_read()
    return redirect("notifications:inbox")
