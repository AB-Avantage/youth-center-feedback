from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import get_language

from .forms import FeedbackAdminUserAddForm, FeedbackAdminUserChangeForm, StaffCreateForm
from .models import StaffMember, Submission, SubmissionEvent
from .operations import archive_submission, create_staff, staff_name
from .texts import TEXTS


admin.site.index_template = "feedback/admin_index.html"


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

    def save_model(self, request, obj, form, change):
        before = Submission.objects.get(pk=obj.pk) if change else None
        if before and before.archived_at and obj.status != Submission.Status.CLOSED:
            obj.archived_at = None
            obj.archived_by = None
        super().save_model(request, obj, form, change)
        if before and before.status != obj.status:
            if obj.status == Submission.Status.CLOSED and not obj.archived_at:
                archive_submission(obj, request.user)
            else:
                SubmissionEvent.objects.create(submission=obj, action=SubmissionEvent.Action.STATUS_CHANGED, actor=request.user, actor_name=staff_name(request.user), text=f"Status changed to {obj.get_status_display()}.")


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "created_at")
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("user", "full_name", "email", "phone", "created_by", "created_at")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def add_view(self, request, form_url="", extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        language = "ar" if request.LANGUAGE_CODE.startswith("ar") else "en"
        form = StaffCreateForm(request.POST or None, language=language)
        if request.method == "POST" and form.is_valid():
            try:
                create_staff(form.cleaned_data, request.user)
            except IntegrityError:
                form.add_error(None, TEXTS[language]["staff_duplicate"])
            else:
                return HttpResponseRedirect(reverse("admin:feedback_staffmember_changelist"))
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": TEXTS[language]["create_staff"],
            "form": form,
            **(extra_context or {}),
        }
        return TemplateResponse(request, "feedback/admin_staff_add.html", context)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(get_user_model())


class PortalStaffFilter(admin.SimpleListFilter):
    title = "Staff portal"
    parameter_name = "portal_staff"

    def __init__(self, request, params, model, model_admin):
        self.title = TEXTS["ar" if (get_language() or "en").startswith("ar") else "en"]["staff_portal"]
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        copy = TEXTS["ar" if (get_language() or "en").startswith("ar") else "en"]
        return (("yes", copy["yes"]), ("no", copy["no"]))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(staff_member__isnull=False)
        if self.value() == "no":
            return queryset.filter(staff_member__isnull=True)
        return queryset


@admin.register(get_user_model())
class FeedbackUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "account_type", "staff_phone", "is_active")
    list_filter = (PortalStaffFilter, "is_superuser", "is_active")
    add_form = FeedbackAdminUserAddForm
    form = FeedbackAdminUserChangeForm
    add_fieldsets = ((None, {"classes": ("wide",), "fields": (
        "username", "email", "first_name", "last_name", "usable_password", "password1", "password2", "portal_staff", "staff_phone",
    )}),)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Staff portal", {"fields": ("portal_staff", "staff_phone")}),
        ("Permissions", {"fields": ("is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        copy = TEXTS["ar" if request.LANGUAGE_CODE.startswith("ar") else "en"]
        return tuple((copy["staff_portal"] if title == "Staff portal" else title, options) for title, options in fieldsets)

    def save_model(self, request, obj, form, change):
        profile = StaffMember.objects.filter(user=obj).first() if change else None
        enabled = form.cleaned_data["portal_staff"]
        if enabled or profile:
            obj.is_staff = False
        super().save_model(request, obj, form, change)
        if enabled:
            full_name = f"{obj.first_name} {obj.last_name}".strip()
            StaffMember.objects.update_or_create(user=obj, defaults={
                "full_name": full_name,
                "email": obj.email.lower(),
                "phone": form.cleaned_data["staff_phone"],
                **({"created_by": request.user} if profile is None else {}),
            })
        elif profile:
            profile.delete()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("staff_member")

    @admin.display(description="Account type")
    def account_type(self, obj):
        labels = TEXTS["ar" if get_language().startswith("ar") else "en"]
        if obj.is_superuser:
            return labels["role_admin"]
        if hasattr(obj, "staff_member"):
            return labels["role_staff"]
        return labels["role_other"]

    @admin.display(description="Staff phone")
    def staff_phone(self, obj):
        return obj.staff_member.phone if hasattr(obj, "staff_member") else ""
