import json
from pathlib import Path


_arabic_data = json.loads(
    (Path(__file__).resolve().parent / "translations" / "ar.json").read_text(encoding="utf-8")
)

TEXTS = {
    "ar": _arabic_data["ui"],
    "en": {
        "direction": "ltr",
        "site_title": "Youth Center Complaints and Suggestions",
        "page_title": "Submit a complaint or suggestion",
        "intro": "Select the youth center and request type, enter your phone number, and describe your request.",
        "facility": "Youth center",
        "choose_facility": "Select a youth center",
        "category": "Request type",
        "choose_category": "Select a request type",
        "report": "Complaint",
        "recommendation": "Suggestion",
        "phone": "Phone number",
        "message": "Complaint or suggestion details",
        "submit": "Submit request",
        "empty_facilities": "No youth centers are available right now. Please try again later.",
        "missing_phone": "This phone number is not linked to an active EZYXS customer account.",
        "empty_message": "Please describe your request.",
        "invalid_phone": "Enter a valid phone number.",
        "success_title": "Your request has been submitted",
        "reference": "Request number",
        "another": "Submit another request",
        "unavailable_title": "Service temporarily unavailable",
        "unavailable_message": "EZYXS data is currently unavailable. Please try again later.",
        "required_error": "This field is required.",
        "invalid_choice_error": "Select a valid option.",
        "max_length_error": "This text must not exceed %(limit_value)d characters.",
        "language_link": "Arabic",
    },
}

FACILITY_NAMES_AR = {int(key): value for key, value in _arabic_data["facility_names"].items()}

TEXTS["en"].update({
    "name": "Full name (optional)", "email": "Email (optional)", "optional": "Optional",
    "intro": "Choose a youth center and request type, then describe what happened. Contact details are optional.",
    "no_facility_match": "No youth center matches your search.",
    "show_centers": "Show youth centers", "create_tab": "New complaint or suggestion", "track_tab": "Track a request",
    "save_code": "Save this eight-digit code. You need it to follow up on your request.",
    "tracking_code": "Tracking code", "lookup": "Find request", "not_found": "No request was found for that code.",
    "tracking_intro": "Enter the eight-digit code you received after submitting.", "request_details": "Request details",
    "timeline": "Activity history", "reply": "Reply", "reply_to_staff": "Respond to staff", "waiting_staff": "Waiting for a staff reply",
    "waiting_customer": "Waiting for your response", "archived_message": "This request has been archived.",
    "status": "Status", "submitted_at": "Submitted", "rate_limited": "Too many attempts. Please try again later.",
    "staff_portal": "Staff portal", "dashboard": "Dashboard", "active_complaints": "Active requests",
    "archived_complaints": "Archived requests", "team": "Staff members", "all_users": "All users", "login": "Sign in",
    "login_intro": "Use your registered email or phone number and password.", "identity": "Email or phone number",
    "password": "Password", "forgot_password": "Forgot password?", "send_otp": "Send code",
    "forgot_intro": "Enter your registered email address to receive a one-time code.",
    "otp_sent": "If your email is registered, a code has been sent. Check your inbox and spam folder.",
    "otp": "One-time code", "new_password": "New password", "confirm_password": "Confirm password",
    "reset_password": "Reset password", "invalid_otp": "The code is invalid or expired.",
    "invalid_login": "Invalid email, phone number, or password.", "mail_error": "Email could not be sent right now. Please try again.",
    "sign_out": "Sign out", "total_requests": "Total requests", "total_complaints": "Complaints",
    "total_suggestions": "Suggestions", "active": "Active", "archived": "Archived",
    "center_comparison": "Complaints by youth center", "view_full": "View full text", "view_details": "View details",
    "no_requests": "No requests here yet.", "phone_short": "Phone", "request_type": "Type",
    "customer": "Customer", "anonymous": "Anonymous", "archive": "Archive request",
    "archive_by": "Archived by", "reply_by": "Replied by", "at": "at", "add_staff": "Add staff member",
    "full_name": "Full name", "staff_email": "Email address", "staff_phone": "Phone number",
    "staff_password": "Initial password", "create_staff": "Create staff account", "staff_duplicate": "This email or phone number is already registered.",
    "role_admin": "Admin", "role_staff": "Staff", "role_other": "Other user",
    "portal_staff_checkbox": "Is staff (staff portal)",
    "portal_staff_help": "Allows login to the staff portal. Requires an email, name, and phone number; does not grant Django admin access.",
    "portal_staff_admin_error": "An admin account cannot also be a staff portal account.",
    "yes": "Yes", "no": "No",
    "yes": "Yes", "no": "No",
    "team_intro": "Staff accounts can view all requests and create other staff accounts. Admin accounts are not shown here.",
    "back": "Back", "recent_activity": "Recent activity", "please_wait": "Please wait",
    "invalid_email": "Enter a valid email address.", "invalid_value": "Enter a valid value.",
    "password_mismatch": "Passwords do not match.", "code_error": "Could not create a tracking code. Please try again.",
    "no_staff_reply": "There is no staff reply to respond to yet.", "reply_blocked": "Wait for the customer to respond before replying again.",
    "already_archived": "This request is already archived.", "status_changed": "Status changed",
    "pages": "Pages", "page": "Page", "previous": "Previous", "next": "Next",
    "status_new": "New", "status_reviewing": "Under review", "status_closed": "Closed",
})

TEXTS["ar"].update(_arabic_data["portal"])
