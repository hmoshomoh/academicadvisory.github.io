"""The one grade scale and the one set of recommendation thresholds.

Documented in README.md; nothing else in the codebase may define a second scale.
"""

from decimal import Decimal, ROUND_HALF_UP

# 5.0-point scale.
GRADE_POINTS = {
    "A": Decimal("5"),
    "B": Decimal("4"),
    "C": Decimal("3"),
    "D": Decimal("2"),
    "E": Decimal("1"),
    "F": Decimal("0"),
}
GRADE_CHOICES = [(letter, letter) for letter in GRADE_POINTS]
PASS_MARK_LETTERS = {"A", "B", "C", "D", "E"}

# Recommendation thresholds, on a 5.0 scale.
PROBATION_BELOW = Decimal("1.50")
WARNING_BELOW = Decimal("2.50")


def quantize(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def weighted_average(pairs):
    """Credit-weighted grade-point average for (credit_units, grade_letter) pairs.

    Returns None when there is nothing to average, so callers never divide by zero.
    """
    total_units = Decimal("0")
    total_points = Decimal("0")
    for units, letter in pairs:
        units = Decimal(units)
        if units <= 0:
            continue
        total_units += units
        total_points += units * GRADE_POINTS[letter]
    if total_units == 0:
        return None
    return quantize(total_points / total_units)


def standing_for(gpa):
    """Which band a GPA falls in: 'probation', 'warning' or 'satisfactory'."""
    if gpa is None:
        return None
    if gpa < PROBATION_BELOW:
        return "probation"
    if gpa < WARNING_BELOW:
        return "warning"
    return "satisfactory"
