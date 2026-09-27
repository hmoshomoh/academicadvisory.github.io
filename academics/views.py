from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import adviser_required, student_required
from accounts.models import Student

from . import recommendations
from .forms import AdvisoryRequestForm, AdvisoryResponseForm
from .models import AcademicRecord, AdvisoryRequest


def _student_of(request):
    return get_object_or_404(Student, user=request.user)


@student_required
def student_overview(request):
    """A student's own GPA per semester, CGPA and generated recommendations."""
    student = _student_of(request)
    records = student.academic_records.prefetch_related(
        "course_results", "recommendations"
    )
    semesters = [
        {"record": record, "gpa": record.gpa(), "recommendations": list(record.recommendations.all())}
        for record in records
    ]
    return render(
        request,
        "academics/student_overview.html",
        {
            "student": student,
            "semesters": semesters,
            "cgpa": recommendations.cgpa_for(student),
            "advisory_requests": student.advisory_requests.all()[:10],
        },
    )


@student_required
def advisory_request_create(request):
    student = _student_of(request)
    if request.method == "POST":
        form = AdvisoryRequestForm(request.POST)
        if form.is_valid():
            advisory = form.save(commit=False)
            advisory.student = student
            advisory.adviser = student.adviser
            advisory.save()
            if student.adviser is None:
                messages.warning(
                    request,
                    "Request saved, but you have no adviser assigned yet — "
                    "an admin needs to assign one before it can be answered.",
                )
            else:
                messages.success(request, "Your adviser has been sent your request.")
            return redirect("academics:student_overview")
    else:
        form = AdvisoryRequestForm()
    return render(
        request,
        "academics/advisory_request_form.html",
        {"form": form, "adviser": student.adviser},
    )


@adviser_required
def adviser_students(request):
    """Assigned students only. Scoping is the FK filter here, not the template."""
    adviser = request.user.adviser
    students = adviser.assigned_students.select_related("user").prefetch_related(
        "academic_records__course_results"
    )
    rows = [
        {"student": student, "cgpa": recommendations.cgpa_for(student),
         "record_count": student.academic_records.count()}
        for student in students
    ]
    return render(
        request,
        "academics/adviser_students.html",
        {
            "rows": rows,
            "pending_requests": adviser.advisory_requests.filter(response="").count(),
        },
    )


@adviser_required
def adviser_student_detail(request, student_id):
    adviser = request.user.adviser
    # Scoped queryset: a student who is not assigned to this adviser is a 404,
    # so there is no view that can render another adviser's student.
    student = get_object_or_404(adviser.assigned_students, pk=student_id)
    records = student.academic_records.prefetch_related("course_results", "recommendations")
    semesters = [
        {"record": record, "gpa": record.gpa(), "recommendations": list(record.recommendations.all())}
        for record in records
    ]
    return render(
        request,
        "academics/adviser_student_detail.html",
        {
            "student": student,
            "semesters": semesters,
            "cgpa": recommendations.cgpa_for(student),
            "requests": student.advisory_requests.filter(adviser=adviser),
        },
    )


@adviser_required
def adviser_requests(request):
    adviser = request.user.adviser
    return render(
        request,
        "academics/adviser_requests.html",
        {"requests": adviser.advisory_requests.select_related("student__user")},
    )


@adviser_required
def advisory_respond(request, request_id):
    adviser = request.user.adviser
    advisory = get_object_or_404(adviser.advisory_requests, pk=request_id)
    if request.method == "POST":
        form = AdvisoryResponseForm(request.POST, instance=advisory)
        if form.is_valid():
            advisory = form.save(commit=False)
            advisory.responded_at = timezone.now()
            advisory.save()
            messages.success(request, "Response sent to the student.")
            return redirect("academics:adviser_requests")
    else:
        form = AdvisoryResponseForm(instance=advisory)
    return render(
        request,
        "academics/advisory_respond.html",
        {"form": form, "advisory": advisory},
    )
