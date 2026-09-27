from django.contrib import admin

from . import recommendations
from .models import AcademicRecord, AdvisoryRequest, CourseResult, Recommendation


class CourseResultInline(admin.TabularInline):
    model = CourseResult
    extra = 3


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    """Where results are entered. Saving regenerates the record's recommendations,
    so advice can never drift out of step with the grades it was derived from."""

    list_display = ["student", "session", "semester", "gpa"]
    list_filter = ["session", "semester", "student__adviser"]
    search_fields = ["student__matric_number", "student__user__last_name"]
    inlines = [CourseResultInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        recommendations.generate_for_record(form.instance)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    """Read-only: recommendations are rule-generated, never hand-authored."""

    list_display = ["record", "kind", "gpa_at_generation", "generated_at"]
    list_filter = ["kind"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AdvisoryRequest)
class AdvisoryRequestAdmin(admin.ModelAdmin):
    list_display = ["student", "adviser", "subject", "answered", "created_at"]
    list_filter = ["adviser"]
