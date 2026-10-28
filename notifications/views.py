from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def inbox(request):
    """A user's own notifications. Scoped by recipient, so no cross-user reads."""
    return render(
        request,
        "notifications/inbox.html",
        {"notifications": Notification.objects.for_user(request.user)[:100]},
    )


@require_POST
@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification.objects.for_user(request.user), pk=pk)
    notification.mark_read()
    return redirect("notifications:inbox")


@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.for_user(request.user).unread().update(read_at=timezone.now())
    return redirect("notifications:inbox")
