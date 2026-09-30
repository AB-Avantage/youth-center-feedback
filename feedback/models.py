from django.db import models


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
    category = models.CharField("Request type", max_length=20, choices=Category.choices)
    message = models.TextField("Message", max_length=5000)
    customer_id = models.PositiveBigIntegerField("EZYXS customer ID", null=True, blank=True)
    customer_name = models.CharField("Customer name", max_length=255, blank=True)
    customer_phone = models.CharField("Phone number", max_length=15)
    customer_email = models.EmailField("Email address", blank=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField("Submitted at", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Submission"
        verbose_name_plural = "Submissions"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"#{self.pk} - {self.get_category_display()} - {self.facility_name}"
