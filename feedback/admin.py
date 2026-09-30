from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "facility_name", "customer_name", "customer_phone", "identity_status", "status", "created_at")
    list_filter = ("category", "status", "facility_name", "created_at")
    search_fields = ("=id", "facility_name", "customer_name", "customer_phone", "message")
    readonly_fields = ("facility_id", "facility_name", "category", "message", "customer_id", "customer_name", "customer_phone", "customer_email", "identity_status", "created_at")
    fields = ("facility_name", "facility_id", "category", "message", "customer_name", "customer_phone", "customer_email", "customer_id", "identity_status", "created_at", "status")
    list_per_page = 50
    actions = None

    @admin.display(description="Customer match")
    def identity_status(self, obj):
        return "Matched in EZYXS" if obj.customer_id else "Phone number only"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
