from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Adviser, Student

from . import grading


class AcademicRecord(models.Model):
    """One semester of results for one student."""

    SEMESTERS = [(1, "First semester"), (2, "Second semester")]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="academic_records"
    )
    session = models.CharField(max_length=16, help_text="e.g. 2025/2026")
    semester = models.PositiveSmallIntegerField(choices=SEMESTERS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "semester"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "session", "semester"],
                name="one_record_per_student_session_semester",
            )
        ]

    def __str__(self):
        return "{} {} S{}".format(self.student.matric_number, self.session, self.semester)

    @property
    def label(self):
        return "{} — {}".format(self.session, self.get_semester_display())

    def grade_pairs(self):
        return [(c.credit_units, c.grade) for c in self.course_results.all()]

    def gpa(self):
        """Credit-weighted GPA for this semester, or None with no courses."""
        return grading.weighted_average(self.grade_pairs())

    def total_units(self):
        return sum(c.credit_units for c in self.course_results.all())

    def failed_courses(self):
        return [c for c in self.course_results.all() if c.grade not in grading.PASS_MARK_LETTERS]


class CourseResult(models.Model):
    """A single course's credit units and grade inside an AcademicRecord."""

    record = models.ForeignKey(
        AcademicRecord, on_delete=models.CASCADE, related_name="course_results"
    )
    course_code = models.CharField(max_length=16)
    course_title = models.CharField(max_length=160, blank=True)
    credit_units = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    grade = models.CharField(max_length=1, choices=grading.GRADE_CHOICES)

    class Meta:
        ordering = ["course_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["record", "course_code"], name="one_result_per_course_per_record"
            )
        ]

    def __str__(self):
        return "{} {}".format(self.course_code, self.grade)

    @property
    def grade_points(self):
        return grading.GRADE_POINTS[self.grade] * self.credit_units


class Recommendation(models.Model):
    """Rule-generated advice derived from an AcademicRecord. Never hand-written."""

    COURSE_ADVICE = "course_advice"
    WARNING = "warning"
    PROBATION_ALERT = "probation_alert"
    KINDS = [
        (COURSE_ADVICE, "Course advice"),
        (WARNING, "Warning"),
        (PROBATION_ALERT, "Probation alert"),
    ]
    SEVERITY_CSS = {
        COURSE_ADVICE: "info",
        WARNING: "warning",
        PROBATION_ALERT: "danger",
    }

    record = models.ForeignKey(
        AcademicRecord, on_delete=models.CASCADE, related_name="recommendations"
    )
    kind = models.CharField(max_length=32, choices=KINDS)
    message = models.TextField()
    gpa_at_generation = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind"]
        constraints = [
            models.UniqueConstraint(
                fields=["record", "kind"], name="one_recommendation_per_kind_per_record"
            )
        ]

    def __str__(self):
        return "{} for {}".format(self.get_kind_display(), self.record)

    @property
    def css_class(self):
        return self.SEVERITY_CSS.get(self.kind, "secondary")


class AdvisoryRequest(models.Model):
    """A student's question to their assigned adviser, and the adviser's reply."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="advisory_requests"
    )
    adviser = models.ForeignKey(
        Adviser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="advisory_requests",
    )
    subject = models.CharField(max_length=160)
    body = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "{}: {}".format(self.student.matric_number, self.subject)

    @property
    def answered(self):
        return bool(self.response)
