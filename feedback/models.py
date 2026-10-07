from django.conf import settings
from django.db import models
from django.utils import timezone


class Submission(models.Model):
    class Category(models.TextChoices):
        REPORT = "report", "Complaint"
        RECOMMENDATION = "recommendation", "Suggestion"

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWING = "reviewing", "Under review"
        CLOSED = "closed", "Closed"

    facility_id = models.PositiveBigIntegerField("Youth center ID")
    facility_name = models.CharField("Youth center", max_length=100)
    tracking_code = models.CharField(max_length=8, unique=True)
    category = models.CharField("Request type", max_length=20, choices=Category.choices)
    message = models.TextField("Message", max_length=5000)
    customer_id = models.PositiveBigIntegerField("EZYXS customer ID", null=True, blank=True)
    customer_name = models.CharField("Customer name", max_length=255, blank=True)
    customer_phone = models.CharField("Phone number", max_length=15, blank=True)
    customer_email = models.EmailField("Email address", blank=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField("Submitted at", auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="archived_submissions")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Submission"
        verbose_name_plural = "Submissions"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"#{self.pk} - {self.get_category_display()} - {self.facility_name}"


class StaffMember(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_member")
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_staff_members")

    def __str__(self):
        return self.full_name


class SubmissionEvent(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        STAFF_REPLY = "staff_reply", "Staff reply"
        CUSTOMER_REPLY = "customer_reply", "Customer reply"
        ARCHIVED = "archived", "Archived"
        STATUS_CHANGED = "status_changed", "Status changed"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="events")
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    actor_name = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class PasswordResetOTP(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="password_resets")
    code_hash = models.CharField(max_length=128)
    sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)


class APIToken(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="api_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)


class RateLimitBucket(models.Model):
    key = models.CharField(max_length=64, unique=True)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
