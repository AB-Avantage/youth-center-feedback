from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path

from feedback.views import submission_create, submission_success


admin.site.site_header = "Complaints and Suggestions Administration"
admin.site.site_title = "Complaints and Suggestions"
admin.site.index_title = "Submissions"

urlpatterns = [
    path("", lambda request: redirect("submission_create_ar")),
    path("ar/", submission_create, {"language": "ar"}, name="submission_create_ar"),
    path("en/", submission_create, {"language": "en"}, name="submission_create_en"),
    path("ar/sent/<int:pk>/", submission_success, {"language": "ar"}, name="submission_success_ar"),
    path("en/sent/<int:pk>/", submission_success, {"language": "en"}, name="submission_success_en"),
    path("staff/", admin.site.urls),
]
