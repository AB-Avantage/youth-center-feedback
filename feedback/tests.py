import json
import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import PasswordResetOTP, StaffMember, Submission
from .admin import SubmissionAdmin
from .operations import OperationError, archive_submission, create_staff, create_submission, reply_to_submission, reset_password, send_reset_otp
from .services import Facility, active_facilities
from .texts import TEXTS


FACILITY = Facility(7, "Youth Center", "Youth Center")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class FeedbackFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser("owner", "owner@example.com", "StrongAdminPassword123!")
        self.staff = create_staff({"full_name": "Staff One", "email": "staff@example.com", "phone": "01012345678", "password": "StrongStaffPassword123!"}, self.admin)

    def submission(self):
        return create_submission({"category": "report", "message": "The center needs repair", "name": "", "phone": "", "email": ""}, FACILITY)

    def api(self, path, data, token=None):
        headers = {"content_type": "application/json"}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(path, json.dumps(data), **headers)

    @patch("feedback.views.active_facilities", return_value=[FACILITY])
    def test_optional_contact_and_tracking_code_in_both_languages(self, _):
        for language in ("en", "ar"):
            page = self.client.get(f"/{language}/")
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, 'data-facility-combobox')
            self.assertContains(page, 'role="combobox"')
            self.assertContains(page, 'feedback/football.svg')
            self.assertNotContains(page, 'data-facility-search=')
            response = self.client.post(f"/{language}/", {"facility": "7", "category": "report", "message": "A clear complaint"}, follow=True)
            self.assertEqual(response.status_code, 200)
            code = response.context["reference"]
            self.assertRegex(code, r"^[0-9]{8}$")
            self.assertContains(response, code)
            item = Submission.objects.get(tracking_code=code)
            self.assertEqual(item.customer_phone, "")
            self.assertEqual(item.events.count(), 1)

    @patch("feedback.views.active_facilities", return_value=[FACILITY])
    def test_youth_center_must_be_selected_from_the_list(self, _):
        response = self.client.post("/en/", {"facility": "999", "category": "report", "message": "A clear complaint"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, TEXTS["en"]["invalid_choice_error"])
        self.assertFalse(Submission.objects.exists())

    def test_tracking_requires_correct_code_and_is_rate_limited(self):
        item = self.submission()
        response = self.client.post("/en/track/", {"code": item.tracking_code})
        self.assertContains(response, item.message)
        response = self.client.post("/en/track/", {"code": "11111111"})
        self.assertContains(response, "No request was found")
        for _ in range(18):
            self.client.post("/en/track/", {"code": "11111111"})
        response = self.client.post("/en/track/", {"code": item.tracking_code})
        self.assertContains(response, "Too many attempts")

    def test_staff_login_phone_or_email_and_no_admin_access(self):
        for identity in (self.staff.email, self.staff.phone):
            self.client.post("/staff/login/", {"identity": identity, "password": "StrongStaffPassword123!"})
            self.assertEqual(self.client.get("/staff/").status_code, 200)
            self.assertEqual(self.client.get("/admin/").status_code, 302)
            self.client.post("/staff/logout/")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(self.client.get("/staff/team/").status_code, 200)

    def test_django_admin_supports_arabic_browser_language(self):
        response = self.client.get("/admin/login/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html lang="ar" dir="rtl">')
        self.assertContains(response, "admin/css/rtl.css")
        self.client.force_login(self.admin)
        response = self.client.get("/admin/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertContains(response, TEXTS["ar"]["create_staff"])

    def test_superadmin_creates_staff_from_admin_and_sees_user_lists(self):
        self.client.force_login(self.admin)
        index = self.client.get("/admin/")
        self.assertContains(index, '/admin/auth/user/')
        self.assertContains(index, '/admin/feedback/staffmember/')
        self.assertContains(index, '/admin/feedback/staffmember/add/')
        response = self.client.post('/admin/feedback/staffmember/add/', {
            'full_name': 'Staff Two', 'email': 'two@example.com',
            'phone': '01012345679', 'password': 'AnotherStrongPassword123!',
        })
        self.assertRedirects(response, '/admin/feedback/staffmember/')
        member = StaffMember.objects.get(email='two@example.com')
        self.assertEqual(member.created_by, self.admin)
        self.assertTrue(member.user.check_password('AnotherStrongPassword123!'))
        self.assertFalse(member.user.is_staff)
        self.assertContains(self.client.get('/admin/feedback/staffmember/'), 'Staff Two')
        users = self.client.get('/admin/auth/user/')
        self.assertContains(users, 'owner@example.com')
        self.assertContains(users, 'two@example.com')
        self.assertContains(users, '01012345679')

    def test_admin_staff_creation_rejects_duplicate_and_staff_cannot_access_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post('/admin/feedback/staffmember/add/', {
            'full_name': 'Duplicate Staff', 'email': self.staff.email,
            'phone': '01012345679', 'password': 'AnotherStrongPassword123!',
        })
        self.assertContains(response, TEXTS['en']['staff_duplicate'])
        self.assertEqual(StaffMember.objects.count(), 1)
        self.client.force_login(self.staff.user)
        self.assertRedirects(self.client.get('/admin/feedback/staffmember/add/'), '/admin/login/?next=/admin/feedback/staffmember/add/')

    def test_admin_user_add_checkbox_creates_portal_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'new.portal@example.com', 'email': 'new.portal@example.com',
            'first_name': 'New', 'last_name': 'Staff', 'portal_staff': 'on',
            'staff_phone': '01012345679', 'usable_password': 'true',
            'password1': 'AnotherStrongPassword123!', 'password2': 'AnotherStrongPassword123!',
            '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.status_code == 200 else '')
        user = get_user_model().objects.get(username='new.portal@example.com')
        self.assertEqual(user.staff_member.phone, '01012345679')
        self.assertFalse(user.is_staff)
        self.client.logout()
        self.assertRedirects(self.client.post('/staff/login/', {
            'identity': 'new.portal@example.com', 'password': 'AnotherStrongPassword123!',
        }), '/staff/')

    def test_admin_user_edit_checkbox_enables_and_disables_portal_staff(self):
        user = get_user_model().objects.create_user(
            username='existing@example.com', email='existing@example.com',
            password='AnotherStrongPassword123!', first_name='Existing', last_name='User', is_staff=True,
        )
        self.client.force_login(self.admin)
        url = f'/admin/auth/user/{user.pk}/change/'
        response = self.client.post(url, {
            'username': user.username, 'email': user.email, 'first_name': user.first_name,
            'last_name': user.last_name, 'is_active': 'on', 'portal_staff': 'on',
            'staff_phone': '01012345679',
            'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': user.date_joined.strftime('%H:%M:%S'), '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.status_code == 200 else '')
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertEqual(user.staff_member.email, 'existing@example.com')
        self.client.logout()
        self.assertRedirects(self.client.post('/staff/login/', {
            'identity': user.email, 'password': 'AnotherStrongPassword123!',
        }), '/staff/')
        self.client.force_login(self.admin)
        response = self.client.post(url, {
            'username': user.username, 'email': user.email, 'first_name': user.first_name,
            'last_name': user.last_name, 'is_active': 'on',
            'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': user.date_joined.strftime('%H:%M:%S'), '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302, response.content.decode()[:1000])
        self.assertFalse(StaffMember.objects.filter(user=user).exists())
        self.client.logout()
        response = self.client.post('/staff/login/', {
            'identity': user.email, 'password': 'AnotherStrongPassword123!',
        })
        self.assertContains(response, TEXTS['en']['invalid_login'])

    def test_staff_can_create_staff_but_team_excludes_admin(self):
        self.client.force_login(self.staff.user)
        response = self.client.post("/staff/team/", {"full_name": "Staff Two", "email": "two@example.com", "phone": "01012345679", "password": "AnotherStrongPassword123!"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffMember.objects.filter(email="two@example.com").exists())
        page = self.client.get("/staff/team/")
        self.assertContains(page, "Staff Two")
        self.assertNotContains(page, "owner@example.com")

    def test_staff_reply_waits_for_customer_and_archives_with_audit(self):
        item = self.submission()
        reply_to_submission(item, "We will investigate", user=self.staff.user)
        with self.assertRaises(OperationError):
            reply_to_submission(item, "A second reply", user=self.staff.user)
        reply_to_submission(item, "Thank you", customer=True)
        reply_to_submission(item, "Here is the update", user=self.staff.user)
        archive_submission(item, self.staff.user)
        item.refresh_from_db()
        self.assertIsNotNone(item.archived_at)
        self.assertEqual(item.archived_by, self.staff.user)
        self.assertEqual(list(item.events.values_list("action", flat=True)), ["submitted", "staff_reply", "customer_reply", "staff_reply", "archived"])
        with self.assertRaises(OperationError):
            reply_to_submission(item, "Late response", customer=True)

    def test_web_customer_reply_and_staff_archive_views(self):
        item = self.submission()
        self.client.force_login(self.staff.user)
        self.assertEqual(self.client.post(f"/staff/complaints/{item.pk}/", {"action": "reply", "text": "We are looking into it"}).status_code, 302)
        self.client.post("/staff/logout/")
        response = self.client.post("/en/track/", {"action": "reply", "code": item.tracking_code, "text": "More details"})
        self.assertContains(response, "More details")
        self.client.force_login(self.staff.user)
        self.assertEqual(self.client.post(f"/staff/complaints/{item.pk}/", {"action": "archive"}).status_code, 302)
        self.assertContains(self.client.get("/staff/archived/"), "Staff One")

    def test_otp_sent_expiring_one_use_and_revokes_tokens(self):
        send_reset_otp(self.staff)
        message = mail.outbox[-1].body
        code = re.search(r"\b[0-9]{6}\b", message).group()
        token = self.api("/api/v1/staff/login/", {"identity": self.staff.email, "password": "StrongStaffPassword123!"}).json()["token"]
        self.assertFalse(reset_password(self.staff.email, "000000" if code != "000000" else "111111", "ChangedPassword123!"))
        self.assertTrue(reset_password(self.staff.email, code, "ChangedPassword123!"))
        self.assertFalse(reset_password(self.staff.email, code, "AnotherPassword123!"))
        self.assertEqual(self.client.get("/api/v1/staff/me/", HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 401)
        send_reset_otp(self.staff)
        reset = PasswordResetOTP.objects.latest("id")
        reset.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        reset.save(update_fields=["expires_at"])
        expired_code = re.search(r"\b[0-9]{6}\b", mail.outbox[-1].body).group()
        self.assertFalse(reset_password(self.staff.email, expired_code, "AnotherPassword123!"))

    def test_forgot_page_does_not_reveal_unknown_email(self):
        response = self.client.post("/staff/forgot/", {"email": "missing@example.com"}, follow=True)
        self.assertContains(response, "Check your inbox and spam folder")
        self.assertEqual(len(mail.outbox), 0)

    @patch("feedback.api.active_facilities", return_value=[FACILITY])
    def test_customer_api_create_lookup_and_reply(self, _):
        created = self.api("/api/v1/submissions/", {"facility": "7", "category": "recommendation", "message": "Please add seats"})
        self.assertEqual(created.status_code, 201)
        code = created.json()["tracking_code"]
        looked_up = self.api("/api/v1/submissions/track/", {"code": code})
        self.assertEqual(looked_up.status_code, 200)
        self.assertEqual(looked_up.json()["submission"]["message"], "Please add seats")
        self.assertNotIn("customer_email", looked_up.json()["submission"])
        self.assertNotIn("customer_phone", looked_up.json()["submission"])
        self.assertEqual(self.api("/api/v1/submissions/reply/", {"code": code, "text": "Hello"}).status_code, 409)

    def test_snapshot_works_when_ezyxs_connection_is_unavailable(self):
        class BrokenConnection:
            def cursor(self):
                raise DatabaseError("Unavailable")
        with patch("feedback.services.connections", {"ezyxs": BrokenConnection()}):
            self.assertEqual(len(active_facilities()), 7)

    def test_registered_staff_can_reset_password_from_web(self):
        response = self.client.post("/staff/forgot/?lang=ar", {"email": self.staff.email}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, TEXTS["ar"]["otp_sent"])
        code = re.search(r"\b[0-9]{6}\b", mail.outbox[-1].body).group()
        response = self.client.post("/staff/reset/", {"email": self.staff.email, "code": code, "password": "NewStrongPassword123!", "confirm_password": "NewStrongPassword123!"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post("/staff/login/", {"identity": self.staff.email, "password": "NewStrongPassword123!"}).status_code, 302)

    def test_admin_status_change_is_audited_and_can_reopen(self):
        item = self.submission()
        model_admin = SubmissionAdmin(Submission, AdminSite())
        request = type("Request", (), {"user": self.admin})()
        item.status = Submission.Status.CLOSED
        model_admin.save_model(request, item, None, True)
        item.refresh_from_db()
        self.assertIsNotNone(item.archived_at)
        self.assertEqual(item.events.last().action, "archived")
        item.status = Submission.Status.NEW
        model_admin.save_model(request, item, None, True)
        item.refresh_from_db()
        self.assertIsNone(item.archived_at)
        self.assertEqual(item.events.last().action, "status_changed")

    def test_staff_can_create_colleague_through_api_and_page_lists_all(self):
        token = self.api("/api/v1/staff/login/", {"identity": self.staff.email, "password": "StrongStaffPassword123!"}).json()["token"]
        created = self.api("/api/v1/staff/team/", {"full_name": "Staff Two", "email": "two@example.com", "phone": "01012345679", "password": "AnotherStrongPassword123!"}, token=token)
        self.assertEqual(created.status_code, 201)
        for number in range(26):
            self.submission()
        self.client.force_login(self.staff.user)
        first_page = self.client.get("/staff/active/")
        self.assertContains(first_page, "Next")
        second_page = self.client.get("/staff/active/?page=2")
        self.assertEqual(second_page.context["page"].number, 2)
        api_page = self.client.get("/api/v1/staff/submissions/?page=1", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(api_page.json()["total"], 26)

    def test_staff_api_token_permissions_dashboard_and_team(self):
        self.submission()
        self.assertEqual(self.client.get("/api/v1/staff/dashboard/").status_code, 401)
        signed_in = self.api("/api/v1/staff/login/", {"identity": self.staff.phone, "password": "StrongStaffPassword123!"})
        self.assertEqual(signed_in.status_code, 200)
        token = signed_in.json()["token"]
        dashboard = self.client.get("/api/v1/staff/dashboard/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(dashboard.json()["complaints"], 1)
        team = self.client.get("/api/v1/staff/team/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(len(team.json()["staff"]), 1)
        self.assertNotIn("owner@example.com", team.content.decode())
        self.assertEqual(self.api("/api/v1/staff/logout/", {}, token=token).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/staff/me/", HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 401)

    def test_api_reply_archive_and_history(self):
        item = self.submission()
        token = self.api("/api/v1/staff/login/", {"identity": self.staff.email, "password": "StrongStaffPassword123!"}).json()["token"]
        url = f"/api/v1/staff/submissions/{item.pk}/"
        self.assertEqual(self.api(url + "reply/", {"text": "First"}, token=token).status_code, 201)
        self.assertEqual(self.api(url + "reply/", {"text": "Second"}, token=token).status_code, 409)
        self.assertEqual(self.api("/api/v1/submissions/reply/", {"code": item.tracking_code, "text": "Customer answer"}).status_code, 201)
        self.assertEqual(self.api(url + "reply/", {"text": "Second"}, token=token).status_code, 201)
        self.assertEqual(self.api(url + "archive/", {}, token=token).status_code, 200)
        detail = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}").json()["submission"]
        self.assertEqual(len(detail["events"]), 5)
        self.assertEqual(detail["archived_by"], "Staff One")
