"""Rule-based recommendation generation.

Recommendations are derived from GPA thresholds and the record's failed courses.
Nothing here is hand-authored per student, and re-running it for the same record
updates the existing rows instead of adding duplicates.
"""

from . import grading
from .models import Recommendation


def _retake_clause(record):
    failed = record.failed_courses()
    if not failed:
        return ""
    codes = ", ".join(c.course_code for c in failed)
    return " Retake the following in your next available semester: {}.".format(codes)


def _rules(record, gpa):
    """Which recommendations apply, as (kind, message) pairs."""
    standing = grading.standing_for(gpa)
    retake = _retake_clause(record)
    if standing == "probation":
        return [(
            Recommendation.PROBATION_ALERT,
            "Your GPA of {gpa} for {label} is below the probation threshold of {limit}. "
            "You are at risk of academic probation. Book a session with your adviser "
            "before registering for the next semester and reduce your course load.{retake}".format(
                gpa=gpa, label=record.label, limit=grading.PROBATION_BELOW, retake=retake
            ),
        )]
    if standing == "warning":
        return [(
            Recommendation.WARNING,
            "Your GPA of {gpa} for {label} is below the {limit} mark. Treat this as a "
            "warning: prioritise your weakest courses, attend tutorials, and check in "
            "with your adviser this semester.{retake}".format(
                gpa=gpa, label=record.label, limit=grading.WARNING_BELOW, retake=retake
            ),
        )]
    if standing == "satisfactory":
        return [(
            Recommendation.COURSE_ADVICE,
            "Your GPA of {gpa} for {label} is satisfactory. Keep your current study "
            "pattern, and consider taking on electives that build on your strongest "
            "courses.{retake}".format(gpa=gpa, label=record.label, retake=retake),
        )]
    return []


def generate_for_record(record):
    """Regenerate this record's recommendations. Idempotent.

    Kinds that no longer apply are removed, so a record never carries a stale
    probation alert after its results are corrected.
    """
    gpa = record.gpa()
    applicable = _rules(record, gpa)
    kept = []
    for kind, message in applicable:
        recommendation, _ = Recommendation.objects.update_or_create(
            record=record,
            kind=kind,
            defaults={"message": message, "gpa_at_generation": gpa},
        )
        kept.append(recommendation)
    record.recommendations.exclude(kind__in=[r.kind for r in kept]).delete()
    return kept


def generate_for_student(student):
    generated = []
    for record in student.academic_records.prefetch_related("course_results"):
        generated.extend(generate_for_record(record))
    return generated


def cgpa_for(student):
    """Credit-weighted CGPA across every semester, or None when there are none."""
    pairs = []
    for record in student.academic_records.prefetch_related("course_results"):
        pairs.extend(record.grade_pairs())
    return grading.weighted_average(pairs)
