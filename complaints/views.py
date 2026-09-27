import csv

from django.contrib import messages
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, student_required
from accounts.models import Student

from . import references, services
from .forms import (
    ADMIN_STATUS_FILTERS,
    ComplaintForm,
    EscalateForm,
    RecategoriseForm,
    ResolveForm,
    ReviewForm,
    TrackingForm,
)
from .models import Complaint, ComplaintCategory, ComplaintStatus, ComplaintStatusLog


# --- Student -----------------------------------------------------------------

@student_required
def submit(request):
    student = get_object_or_404(Student, user=request.user)
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            anonymous = form.cleaned_data["submit_anonymously"]
            complaint = services.submit_complaint(
                category=form.cleaned_data["category"],
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
                attachment=form.cleaned_data.get("attachment"),
                student=student,
                anonymous=anonymous,
            )
            request.session["last_reference"] = complaint.reference
            return redirect("complaints:submitted", reference=complaint.reference)
    else:
        form = ComplaintForm()
    return render(request, "complaints/submit.html", {"form": form})


def submitted(request, reference):
    """Receipt screen: shows the tracking reference once, to whoever just submitted."""
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.session.get("last_reference") != reference:
        return redirect("complaints:track")
    return render(
        request,
        "complaints/submitted.html",
        {"complaint": complaint, "anonymous": complaint.is_anonymous},
    )


@student_required
def my_complaints(request):
    """A student's named complaints.

    Anonymous complaints cannot appear here: they hold no student id, so the
    queryset has nothing to match. That is the point, not an omission.
    """
    student = get_object_or_404(Student, user=request.user)
    return render(
        request,
        "complaints/my_complaints.html",
        {"complaints": Complaint.objects.for_student(student).select_related("category")},
    )


@student_required
def my_complaint_detail(request, pk):
    student = get_object_or_404(Student, user=request.user)
    complaint = get_object_or_404(Complaint.objects.for_student(student), pk=pk)
    return render(
        request,
        "complaints/detail.html",
        {"complaint": complaint, "logs": complaint.status_logs.all(), "viewer": "student"},
    )


# --- Public tracking ---------------------------------------------------------

def track(request):
    """Status lookup by reference, with no login and no identity disclosed."""
    complaint = None
    searched = False
    form = TrackingForm(request.GET or None)
    if request.GET.get("reference"):
        searched = True
        if form.is_valid():
            reference = references.normalise(form.cleaned_data["reference"])
            complaint = Complaint.objects.filter(reference=reference).first()
    context = {
        "form": form,
        "complaint": complaint,
        "searched": searched,
        "logs": complaint.status_logs.all() if complaint else [],
        "updates": complaint.notifications.all() if complaint else [],
    }
    return render(request, "complaints/track.html", context)


# --- Admin -------------------------------------------------------------------

@admin_required
def admin_list(request):
    complaints = Complaint.objects.select_related("category")
    status = request.GET.get("status", "")
    category_id = request.GET.get("category", "")
    if status in ComplaintStatus.values:
        complaints = complaints.filter(status=status)
    if category_id.isdigit():
        complaints = complaints.filter(category_id=int(category_id))
    return render(
        request,
        "complaints/admin_list.html",
        {
            "complaints": complaints,
            "statuses": ADMIN_STATUS_FILTERS,
            "categories": ComplaintCategory.objects.all(),
            "selected_status": status,
            "selected_category": category_id,
            "open_count": Complaint.objects.exclude(status=ComplaintStatus.RESOLVED).count(),
        },
    )


@admin_required
def admin_detail(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("category"), pk=pk)
    return render(
        request,
        "complaints/admin_detail.html",
        {
            "complaint": complaint,
            "logs": complaint.status_logs.select_related("actor"),
            # Each form is prefixed: all four share a `note` field, and without a
            # prefix they would render four elements with the same id, so every
            # <label for="id_note"> would point at the first textarea on the page.
            "recategorise_form": RecategoriseForm(
                prefix="categorise", initial={"category": complaint.category}
            ),
            "review_form": ReviewForm(prefix="review"),
            "escalate_form": EscalateForm(prefix="escalate"),
            "resolve_form": ResolveForm(prefix="resolve"),
        },
    )


@admin_required
def admin_action(request, pk, action):
    """Categorise, review, escalate or resolve. Every branch writes a log row."""
    complaint = get_object_or_404(Complaint, pk=pk)
    forms_by_action = {
        "categorise": RecategoriseForm,
        "review": ReviewForm,
        "escalate": EscalateForm,
        "resolve": ResolveForm,
    }
    if request.method != "POST" or action not in forms_by_action:
        return redirect("complaints:admin_detail", pk=pk)

    form = forms_by_action[action](request.POST, prefix=action)
    if not form.is_valid():
        messages.error(request, "That action needs a note — nothing was changed.")
        return redirect("complaints:admin_detail", pk=pk)

    if action == "categorise":
        services.recategorise(
            complaint=complaint,
            actor=request.user,
            category=form.cleaned_data["category"],
            note=form.cleaned_data["note"],
        )
        messages.success(request, "Category updated and logged.")
        return redirect("complaints:admin_detail", pk=pk)

    to_status, log_action = {
        "review": (ComplaintStatus.UNDER_REVIEW, ComplaintStatusLog.REVIEWED),
        "escalate": (ComplaintStatus.ESCALATED, ComplaintStatusLog.ESCALATED),
        "resolve": (ComplaintStatus.RESOLVED, ComplaintStatusLog.RESOLVED),
    }[action]
    services.record_status_change(
        complaint=complaint,
        actor=request.user,
        action=log_action,
        to_status=to_status,
        note=form.cleaned_data.get("note", ""),
    )
    messages.success(
        request,
        "Complaint moved to {} and logged.".format(ComplaintStatus(to_status).label.lower()),
    )
    return redirect("complaints:admin_detail", pk=pk)


def _humanise_hours(hours):
    """A readable span: 2.4 h, or 18 min, or None when nothing is resolved yet."""
    if hours is None:
        return None
    if hours < 1:
        return "{} min".format(max(1, round(hours * 60)))
    return "{} h".format(round(hours, 1))


@admin_required
def dashboard(request):
    """Volume, category and status breakdowns, and average resolution time."""
    total = Complaint.objects.count()
    resolved = Complaint.objects.filter(status=ComplaintStatus.RESOLVED)
    average = resolved.exclude(resolved_at__isnull=True).aggregate(
        avg=Avg(
            ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())
        )
    )["avg"]
    average_hours = average.total_seconds() / 3600.0 if average is not None else None
    # Rendered separately: a genuine 0.0 hours is falsy in a template, and would
    # otherwise show as "no data" for complaints resolved within the same minute.
    average_display = _humanise_hours(average_hours)

    by_category = list(
        ComplaintCategory.objects.annotate(total=Count("complaints")).order_by("-total")
    )
    counts = dict(
        Complaint.objects.values_list("status").annotate(total=Count("id"))
    )
    by_status = [
        {"label": label, "value": value, "total": counts.get(value, 0)}
        for value, label in ComplaintStatus.choices
    ]
    return render(
        request,
        "complaints/dashboard.html",
        {
            "total": total,
            "resolved_count": resolved.count(),
            "open_count": total - resolved.count(),
            "anonymous_count": Complaint.objects.anonymous().count(),
            "average_hours": average_hours,
            "average_display": average_display,
            "by_category": by_category,
            "by_status": by_status,
            "max_category_total": max([c.total for c in by_category], default=0),
        },
    )


@admin_required
def export_csv(request):
    """Report export.

    The submitter column is written from `submitter_label`, which returns
    "Anonymous" for an anonymous complaint — the export has no access to an
    identity because none was stored.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="complaints-report.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "reference", "submitted_at", "submitter", "anonymous", "category",
        "subject", "status", "resolved_at", "resolution_hours",
    ])
    for complaint in Complaint.objects.select_related("category"):
        hours = complaint.resolution_hours()
        writer.writerow([
            complaint.reference,
            complaint.created_at.isoformat(timespec="seconds"),
            complaint.submitter_label,
            "yes" if complaint.is_anonymous else "no",
            complaint.category.name,
            complaint.subject,
            complaint.get_status_display(),
            complaint.resolved_at.isoformat(timespec="seconds") if complaint.resolved_at else "",
            "" if hours is None else round(hours, 2),
        ])
    return response
