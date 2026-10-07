import hashlib
import json
import logging
from functools import wraps

from django.db import IntegrityError
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import OTPRequestForm, PasswordResetForm, ReplyForm, StaffCreateForm, StaffLoginForm, SubmissionForm, TrackingForm
from .models import APIToken, StaffMember, Submission
from .operations import OperationError, archive_submission, create_staff, create_submission, find_staff, issue_api_token, rate_limit, reply_to_submission, request_ip, reset_password, send_reset_otp, staff_from_token
from .services import EZYXSUnavailable, active_facilities


logger = logging.getLogger(__name__)


def body(request):
    try:
        value = json.loads(request.body or b"{}")
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def invalid(form):
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


def forbidden(message="Forbidden"):
    return JsonResponse({"error": message}, status=403)


def token_staff(request):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return staff_from_token(authorization[7:].strip())


def protected(view):
    @csrf_exempt
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        staff = token_staff(request)
        if not staff:
            return JsonResponse({"error": "A valid staff bearer token is required."}, status=401)
        return view(request, staff, *args, **kwargs)
    return wrapped


def serialize_event(event):
    return {"action": event.action, "actor": event.actor_name, "text": event.text, "at": event.created_at.isoformat()}


def serialize_submission(item, detail=False):
    data = {"id": item.pk, "tracking_code": item.tracking_code, "facility_id": item.facility_id, "facility_name": item.facility_name, "category": item.category, "message": item.message if detail else item.message[:180], "customer_name": item.customer_name, "customer_phone": item.customer_phone, "customer_email": item.customer_email, "status": item.status, "created_at": item.created_at.isoformat(), "archived_at": item.archived_at.isoformat() if item.archived_at else None, "archived_by": item.archived_by.staff_member.full_name if item.archived_by and hasattr(item.archived_by, "staff_member") else None}
    if detail:
        data["events"] = [serialize_event(event) for event in item.events.all()]
    return data


def serialize_customer_submission(item):
    return {"tracking_code": item.tracking_code, "facility_name": item.facility_name, "category": item.category, "message": item.message, "status": item.status, "archived_at": item.archived_at.isoformat() if item.archived_at else None, "created_at": item.created_at.isoformat(), "events": [serialize_event(event) for event in item.events.all()]}


@require_http_methods(["GET"])
def facilities_api(request):
    language = "ar" if request.GET.get("lang") == "ar" else "en"
    try:
        facilities = active_facilities()
    except EZYXSUnavailable:
        return JsonResponse({"error": "Facilities are unavailable."}, status=503)
    return JsonResponse({"facilities": [{"id": item.id, "name": item.label(language)} for item in facilities]})


@csrf_exempt
@require_http_methods(["POST"])
def create_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_submit", request_ip(request), 15, 3600):
        return JsonResponse({"error": "Too many requests."}, status=429)
    try:
        facilities = active_facilities()
    except EZYXSUnavailable:
        return JsonResponse({"error": "Facilities are unavailable."}, status=503)
    form = SubmissionForm(data, facilities=facilities, language="en")
    if not form.is_valid():
        return invalid(form)
    try:
        submission = create_submission(form.cleaned_data, form.facilities[form.cleaned_data["facility"]])
    except OperationError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    return JsonResponse({"tracking_code": submission.tracking_code, "message": "Save this code to follow up on your request."}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def track_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_lookup", request_ip(request), 20, 3600):
        return JsonResponse({"error": "Too many requests."}, status=429)
    form = TrackingForm(data)
    if not form.is_valid():
        return invalid(form)
    item = Submission.objects.filter(tracking_code=form.cleaned_data["code"]).first()
    if not item:
        return JsonResponse({"error": "Code not found."}, status=404)
    return JsonResponse({"submission": serialize_customer_submission(item)})


@csrf_exempt
@require_http_methods(["POST"])
def customer_reply_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_customer_reply", request_ip(request), 20, 3600):
        return JsonResponse({"error": "Too many requests."}, status=429)
    code_form, reply_form = TrackingForm(data), ReplyForm(data)
    if not code_form.is_valid():
        return invalid(code_form)
    if not reply_form.is_valid():
        return invalid(reply_form)
    item = Submission.objects.filter(tracking_code=code_form.cleaned_data["code"]).first()
    if not item:
        return JsonResponse({"error": "Code not found."}, status=404)
    try:
        event = reply_to_submission(item, reply_form.cleaned_data["text"], customer=True)
    except OperationError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse({"event": serialize_event(event)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_staff_login", request_ip(request), 10, 900):
        return JsonResponse({"error": "Too many requests."}, status=429)
    form = StaffLoginForm(data)
    if not form.is_valid():
        return invalid(form)
    user = find_staff(form.cleaned_data["identity"], form.cleaned_data["password"])
    if not user:
        return JsonResponse({"error": "Invalid credentials."}, status=401)
    return JsonResponse({"token": issue_api_token(user.staff_member), "expires_in": 2592000})


@csrf_exempt
@require_http_methods(["POST"])
def forgot_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_reset_request", request_ip(request), 5, 3600):
        return JsonResponse({"error": "Too many requests."}, status=429)
    form = OTPRequestForm(data)
    if not form.is_valid():
        return invalid(form)
    staff = StaffMember.objects.filter(email__iexact=form.cleaned_data["email"], user__is_active=True).first()
    if staff and rate_limit("reset_address", staff.email.lower(), 3, 3600):
        try:
            send_reset_otp(staff)
        except Exception:
            logger.exception("Staff password reset email failed")
    return JsonResponse({"message": "If this email is registered, a code has been sent. Check your inbox and spam folder."})


@csrf_exempt
@require_http_methods(["POST"])
def reset_api(request):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not rate_limit("api_reset_verify", request_ip(request), 12, 3600):
        return JsonResponse({"error": "Too many requests."}, status=429)
    form = PasswordResetForm(data)
    if not form.is_valid():
        return invalid(form)
    if not reset_password(form.cleaned_data["email"], form.cleaned_data["code"], form.cleaned_data["password"]):
        return JsonResponse({"error": "Invalid or expired code."}, status=400)
    return JsonResponse({"message": "Password updated."})


@protected
@require_http_methods(["POST"])
def logout_api(request, staff):
    raw = request.headers.get("Authorization", "")[7:].strip()
    APIToken.objects.filter(token_hash=hashlib.sha256(raw.encode()).hexdigest(), staff=staff).update(revoked_at=timezone.now())
    return JsonResponse({"message": "Signed out."})


@protected
@require_http_methods(["GET"])
def me_api(request, staff):
    return JsonResponse({"full_name": staff.full_name, "email": staff.email, "phone": staff.phone})


@protected
@require_http_methods(["GET"])
def dashboard_api(request, staff):
    total = Submission.objects.count()
    complaints = Submission.objects.filter(category=Submission.Category.REPORT).count()
    active = Submission.objects.filter(archived_at__isnull=True).count()
    centers = list(Submission.objects.values("facility_id", "facility_name").annotate(complaints=Count("id", filter=Q(category=Submission.Category.REPORT))).order_by("-complaints", "facility_name"))
    return JsonResponse({"total": total, "complaints": complaints, "suggestions": total - complaints, "active": active, "archived": total - active, "centers": centers})


@protected
@require_http_methods(["GET"])
def submissions_api(request, staff):
    archived = request.GET.get("tab") == "archived"
    page = Paginator(Submission.objects.filter(archived_at__isnull=not archived).select_related("archived_by").order_by("-created_at"), 50).get_page(request.GET.get("page"))
    return JsonResponse({"results": [serialize_submission(item) for item in page.object_list], "page": page.number, "pages": page.paginator.num_pages, "total": page.paginator.count})


@protected
@require_http_methods(["GET"])
def detail_api(request, staff, pk):
    item = Submission.objects.filter(pk=pk).select_related("archived_by").first()
    if not item:
        return JsonResponse({"error": "Not found."}, status=404)
    return JsonResponse({"submission": serialize_submission(item, detail=True)})


@protected
@require_http_methods(["POST"])
def staff_reply_api(request, staff, pk):
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    form = ReplyForm(data)
    if not form.is_valid():
        return invalid(form)
    item = Submission.objects.filter(pk=pk).first()
    if not item:
        return JsonResponse({"error": "Not found."}, status=404)
    try:
        event = reply_to_submission(item, form.cleaned_data["text"], user=staff.user)
    except OperationError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse({"event": serialize_event(event)}, status=201)


@protected
@require_http_methods(["POST"])
def archive_api(request, staff, pk):
    item = Submission.objects.filter(pk=pk).first()
    if not item:
        return JsonResponse({"error": "Not found."}, status=404)
    try:
        event = archive_submission(item, staff.user)
    except OperationError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse({"event": serialize_event(event)})


@protected
@require_http_methods(["GET", "POST"])
def team_api(request, staff):
    if request.method == "GET":
        return JsonResponse({"staff": [{"id": person.pk, "full_name": person.full_name, "email": person.email, "phone": person.phone} for person in StaffMember.objects.order_by("full_name")]})
    data = body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    form = StaffCreateForm(data)
    if not form.is_valid():
        return invalid(form)
    try:
        person = create_staff(form.cleaned_data, staff.user)
    except IntegrityError:
        return JsonResponse({"error": "A staff account with this email or phone already exists."}, status=409)
    return JsonResponse({"id": person.pk, "full_name": person.full_name, "email": person.email, "phone": person.phone}, status=201)
