from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path

from feedback import api, views


admin.site.site_header = "Complaints and Suggestions Administration"
admin.site.site_title = "Complaints and Suggestions"
admin.site.index_title = "Submissions"

urlpatterns = [
    path("", lambda request: redirect("submission_create_ar")),
    path("ar/", views.submission_create, {"language": "ar"}, name="submission_create_ar"),
    path("en/", views.submission_create, {"language": "en"}, name="submission_create_en"),
    path("ar/sent/", views.submission_success, {"language": "ar"}, name="submission_success_ar"),
    path("en/sent/", views.submission_success, {"language": "en"}, name="submission_success_en"),
    path("ar/track/", views.submission_track, {"language": "ar"}, name="submission_track_ar"),
    path("en/track/", views.submission_track, {"language": "en"}, name="submission_track_en"),
    path("admin/", admin.site.urls),
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/login/", views.staff_login, name="staff_login"),
    path("staff/logout/", views.staff_logout, name="staff_logout"),
    path("staff/forgot/", views.staff_forgot, name="staff_forgot"),
    path("staff/reset/", views.staff_reset, name="staff_reset"),
    path("staff/active/", views.staff_submissions, name="staff_active"),
    path("staff/archived/", views.staff_submissions, {"archived": True}, name="staff_archived"),
    path("staff/complaints/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("staff/team/", views.staff_team, name="staff_team"),
    path("api/v1/facilities/", api.facilities_api),
    path("api/v1/submissions/", api.create_api),
    path("api/v1/submissions/track/", api.track_api),
    path("api/v1/submissions/reply/", api.customer_reply_api),
    path("api/v1/staff/login/", api.login_api),
    path("api/v1/staff/logout/", api.logout_api),
    path("api/v1/staff/forgot/", api.forgot_api),
    path("api/v1/staff/reset/", api.reset_api),
    path("api/v1/staff/me/", api.me_api),
    path("api/v1/staff/dashboard/", api.dashboard_api),
    path("api/v1/staff/submissions/", api.submissions_api),
    path("api/v1/staff/submissions/<int:pk>/", api.detail_api),
    path("api/v1/staff/submissions/<int:pk>/reply/", api.staff_reply_api),
    path("api/v1/staff/submissions/<int:pk>/archive/", api.archive_api),
    path("api/v1/staff/team/", api.team_api),
]
