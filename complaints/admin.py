from django.contrib import admin

from .models import Complaint, ComplaintCategory, ComplaintStatusLog


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["reference", "subject", "category", "status", "submitter_label", "created_at"]
    list_filter = ["status", "category", "is_anonymous"]
    search_fields = ["reference", "subject"]
    readonly_fields = ["reference", "created_at", "updated_at"]


@admin.register(ComplaintStatusLog)
class ComplaintStatusLogAdmin(admin.ModelAdmin):
    """Read-only in the Django admin too: the trail is append-only everywhere."""

    list_display = ["complaint", "action", "from_status", "to_status", "actor_label", "created_at"]
    list_filter = ["action", "to_status"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
