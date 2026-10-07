import logging
from functools import wraps

from django.contrib.auth import login, logout
from django.db import IntegrityError
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import OTPRequestForm, PasswordResetForm, ReplyForm, StaffCreateForm, StaffLoginForm, SubmissionForm, TrackingForm
from .models import StaffMember, Submission, SubmissionEvent
from .operations import OperationError, archive_submission, create_staff, create_submission, find_staff, is_portal_user, rate_limit, reply_to_submission, request_ip, reset_password, send_reset_otp, staff_name
from .services import EZYXSUnavailable, active_facilities
from .texts import TEXTS


logger = logging.getLogger(__name__)


def page_context(language, **extra):
    return {"language": language, "copy": TEXTS[language], "switch_url": "submission_create_en" if language == "ar" else "submission_create_ar", **extra}


def staff_language(request):
    chosen = request.GET.get("lang")
    if chosen in ("ar", "en"):
        request.session["staff_language"] = chosen
    return request.session.get("staff_language", "en")


def staff_context(request, **extra):
    language = staff_language(request)
    return {"language": language, "copy": TEXTS[language], "portal": True, "switch_query": "?lang=" + ("ar" if language == "en" else "en"), "staff_display_name": staff_name(request.user) if is_portal_user(request.user) else "", **extra}


def portal_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_portal_user(request.user):
            return redirect("staff_login")
        return view(request, *args, **kwargs)
    return wrapped


@require_http_methods(["GET", "POST"])
def submission_create(request, language):
    try:
        facilities = active_facilities()
    except EZYXSUnavailable:
        return render(request, "feedback/unavailable.html", page_context(language), status=503)
    form = SubmissionForm(request.POST or None, facilities=facilities, language=language)
    if request.method == "POST" and form.is_valid():
        if not rate_limit("submit", request_ip(request), 15, 3600):
            form.add_error(None, TEXTS[language]["rate_limited"])
        else:
            try:
                submission = create_submission(form.cleaned_data, form.facilities[form.cleaned_data["facility"]])
            except OperationError as exc:
                form.add_error(None, TEXTS[language].get(exc.code, str(exc)))
            else:
                request.session["last_tracking_code"] = submission.tracking_code
                return redirect("submission_success_" + language)
    return render(request, "feedback/form.html", page_context(language, form=form, active_tab="create"))


def submission_success(request, language):
    code = request.session.pop("last_tracking_code", None)
    if not code:
        return redirect("submission_create_" + language)
    return render(request, "feedback/success.html", page_context(language, reference=code))


@require_http_methods(["GET", "POST"])
def submission_track(request, language):
    form = TrackingForm(request.POST or None, language=language)
    reply_form = ReplyForm(request.POST or None, language=language) if request.POST.get("action") == "reply" else ReplyForm(language=language)
    submission = None
    if request.method == "POST" and form.is_valid():
        if not rate_limit("lookup", request_ip(request), 20, 3600):
            form.add_error(None, TEXTS[language]["rate_limited"])
        else:
            submission = Submission.objects.filter(tracking_code=form.cleaned_data["code"]).first()
            if not submission:
                form.add_error("code", TEXTS[language]["not_found"])
            elif request.POST.get("action") == "reply" and reply_form.is_valid():
                try:
                    reply_to_submission(submission, reply_form.cleaned_data["text"], customer=True)
                except OperationError as exc:
                    reply_form.add_error(None, TEXTS[language].get(exc.code, str(exc)))
                else:
                    reply_form = ReplyForm(language=language)
                    submission.refresh_from_db()
    events = list(submission.events.select_related("actor")) if submission else []
    last_turn = next((event for event in reversed(events) if event.action in (SubmissionEvent.Action.STAFF_REPLY, SubmissionEvent.Action.CUSTOMER_REPLY)), None)
    can_reply = bool(submission and not submission.archived_at and last_turn and last_turn.action == SubmissionEvent.Action.STAFF_REPLY)
    return render(request, "feedback/track.html", page_context(language, switch_url="submission_track_en" if language == "ar" else "submission_track_ar", active_tab="track", form=form, reply_form=reply_form, submission=submission, events=events, can_reply=can_reply))


@require_http_methods(["GET", "POST"])
def staff_login(request):
    if is_portal_user(request.user):
        return redirect("staff_dashboard")
    language = staff_language(request)
    form = StaffLoginForm(request.POST or None, language=language)
    if request.method == "POST" and form.is_valid():
        if not rate_limit("staff_login", request_ip(request), 10, 900):
            form.add_error(None, TEXTS[language]["rate_limited"])
        else:
            user = find_staff(form.cleaned_data["identity"], form.cleaned_data["password"])
            if user:
                login(request, user)
                return redirect("staff_dashboard")
            form.add_error(None, TEXTS[language]["invalid_login"])
    return render(request, "feedback/staff_login.html", {"language": language, "copy": TEXTS[language], "portal": True, "switch_query": "?lang=" + ("ar" if language == "en" else "en"), "form": form})


@require_POST
@portal_required
def staff_logout(request):
    logout(request)
    return redirect("staff_login")


@require_http_methods(["GET", "POST"])
def staff_forgot(request):
    language = staff_language(request)
    form = OTPRequestForm(request.POST or None, language=language)
    if request.method == "POST" and form.is_valid():
        if not rate_limit("reset_request", request_ip(request), 5, 3600):
            form.add_error(None, TEXTS[language]["rate_limited"])
        else:
            staff = StaffMember.objects.filter(email__iexact=form.cleaned_data["email"]).first()
            if staff and staff.user.is_active and rate_limit("reset_address", staff.email.lower(), 3, 3600):
                try:
                    send_reset_otp(staff)
                except Exception:
                    logger.exception("Staff password reset email failed")
            if not form.errors:
                request.session["reset_email"] = form.cleaned_data["email"]
                return redirect("staff_reset")
    return render(request, "feedback/staff_forgot.html", {"language": language, "copy": TEXTS[language], "portal": True, "switch_query": "?lang=" + ("ar" if language == "en" else "en"), "form": form})


@require_http_methods(["GET", "POST"])
def staff_reset(request):
    if not request.session.get("reset_email"):
        return redirect("staff_forgot")
    language = staff_language(request)
    initial = {"email": request.session.get("reset_email", "")}
    form = PasswordResetForm(request.POST or None, initial=initial, language=language)
    if request.method == "POST" and form.is_valid():
        if not rate_limit("reset_verify", request_ip(request), 12, 3600):
            form.add_error(None, TEXTS[language]["rate_limited"])
        elif reset_password(form.cleaned_data["email"], form.cleaned_data["code"], form.cleaned_data["password"]):
            request.session.pop("reset_email", None)
            return redirect("staff_login")
        else:
            form.add_error("code", TEXTS[language]["invalid_otp"])
    return render(request, "feedback/staff_reset.html", {"language": language, "copy": TEXTS[language], "portal": True, "switch_query": "?lang=" + ("ar" if language == "en" else "en"), "form": form})


@portal_required
def staff_dashboard(request):
    all_items = Submission.objects.all()
    total = all_items.count()
    complaints = all_items.filter(category=Submission.Category.REPORT).count()
    suggestions = total - complaints
    active = all_items.filter(archived_at__isnull=True).count()
    facilities = list(all_items.values("facility_id", "facility_name").annotate(total=Count("id"), complaints=Count("id", filter=Q(category=Submission.Category.REPORT))).order_by("-complaints", "facility_name"))
    maximum = max((item["complaints"] for item in facilities), default=1) or 1
    for item in facilities:
        item["percent"] = round(item["complaints"] / maximum * 100)
    return render(request, "feedback/staff_dashboard.html", staff_context(request, total=total, complaints=complaints, suggestions=suggestions, active=active, archived=total-active, facilities=facilities))


@portal_required
def staff_submissions(request, archived=False):
    page = Paginator(Submission.objects.filter(archived_at__isnull=not archived).select_related("archived_by").order_by("-created_at"), 25).get_page(request.GET.get("page"))
    items = list(page.object_list)
    if archived:
        for item in items:
            item.archive_event = item.events.filter(action=SubmissionEvent.Action.ARCHIVED).order_by("-created_at", "-id").first()
            item.latest_staff_reply = item.events.filter(action=SubmissionEvent.Action.STAFF_REPLY).order_by("-created_at", "-id").first()
    return render(request, "feedback/staff_list.html", staff_context(request, items=items, page=page, archived=archived))


@portal_required
@require_http_methods(["GET", "POST"])
def staff_detail(request, pk):
    submission = Submission.objects.filter(pk=pk).select_related("archived_by").first()
    if not submission:
        raise Http404
    form = ReplyForm(request.POST or None, language=staff_language(request))
    error = ""
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "archive":
                archive_submission(submission, request.user)
                return redirect("staff_detail", pk=pk)
            if action == "reply" and form.is_valid():
                reply_to_submission(submission, form.cleaned_data["text"], user=request.user)
                return redirect("staff_detail", pk=pk)
        except OperationError as exc:
            error = TEXTS[staff_language(request)].get(exc.code, str(exc))
    submission.refresh_from_db()
    events = list(submission.events.select_related("actor"))
    last_turn = next((event for event in reversed(events) if event.action in (SubmissionEvent.Action.STAFF_REPLY, SubmissionEvent.Action.CUSTOMER_REPLY)), None)
    can_reply = bool(not submission.archived_at and (not last_turn or last_turn.action != SubmissionEvent.Action.STAFF_REPLY))
    return render(request, "feedback/staff_detail.html", staff_context(request, submission=submission, events=events, form=form, error=error, can_reply=can_reply))


@portal_required
@require_http_methods(["GET", "POST"])
def staff_team(request):
    form = StaffCreateForm(request.POST or None, language=staff_language(request))
    if request.method == "POST" and form.is_valid():
        try:
            create_staff(form.cleaned_data, request.user)
        except IntegrityError:
            form.add_error(None, TEXTS[staff_language(request)]["staff_duplicate"])
        else:
            return redirect("staff_team")
    members = StaffMember.objects.select_related("user").order_by("full_name")
    return render(request, "feedback/staff_team.html", staff_context(request, form=form, members=members))
