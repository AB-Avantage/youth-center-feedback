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
