from django.db import models


class Submission(models.Model):
    class Category(models.TextChoices):
        REPORT = "report", "شكوى"
        RECOMMENDATION = "recommendation", "مقترح"

    class Status(models.TextChoices):
        NEW = "new", "جديد"
        REVIEWING = "reviewing", "قيد المراجعة"
        CLOSED = "closed", "مغلق"

    facility_id = models.PositiveBigIntegerField("رقم مركز الشباب")
    facility_name = models.CharField("مركز الشباب", max_length=100)
    category = models.CharField("النوع", max_length=20, choices=Category.choices)
    message = models.TextField("النص", max_length=5000)
    customer_id = models.PositiveBigIntegerField("رقم عميل EZYXS", null=True, blank=True)
    customer_name = models.CharField("اسم العميل", max_length=255, blank=True)
    customer_phone = models.CharField("رقم التليفون", max_length=15)
    customer_email = models.EmailField("البريد الإلكتروني", blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField("وقت الإرسال", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"#{self.pk} - {self.get_category_display()} - {self.facility_name}"
