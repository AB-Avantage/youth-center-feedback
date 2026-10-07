import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import APIToken, PasswordResetOTP, RateLimitBucket, StaffMember, Submission, SubmissionEvent
from .services import EZYXSUnavailable, find_customer_by_phone, normalize_phone, phone_variants


class OperationError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code


def is_portal_user(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or StaffMember.objects.filter(user=user).exists()))


def staff_name(user):
    if user.is_superuser:
        return "Administrator"
    return user.staff_member.full_name


def rate_limit(scope, identifier, limit, seconds):
    key = hashlib.sha256(f"{scope}:{identifier}".encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateLimitBucket.objects.get_or_create(key=key, defaults={"window_start": now})
        if bucket.window_start <= now - timedelta(seconds=seconds):
            bucket.window_start = now
            bucket.count = 1
            bucket.save(update_fields=["window_start", "count"])
            return True
        RateLimitBucket.objects.filter(pk=bucket.pk).update(count=F("count") + 1)
        bucket.refresh_from_db(fields=["count"])
        return bucket.count <= limit


def request_ip(request):
    # Trust only REMOTE_ADDR; forwarding headers require a configured trusted proxy.
    return request.META.get("REMOTE_ADDR", "unknown")


def create_submission(data, facility):
    phone = data.get("phone", "")
    customer = None
    if phone:
        try:
            customer = find_customer_by_phone(phone)
        except EZYXSUnavailable:
            pass
    for _ in range(10):
        code = f"{secrets.randbelow(90000000) + 10000000:08d}"
        try:
            with transaction.atomic():
                submission = Submission.objects.create(
                    tracking_code=code,
                    facility_id=facility.id,
                    facility_name=facility.label("en"),
                    category=data["category"],
                    message=data["message"],
                    customer_id=customer.id if customer else None,
                    customer_name=data.get("name") or (customer.name if customer else ""),
                    customer_phone=phone or "",
                    customer_email=data.get("email") or (customer.email if customer else ""),
                )
                SubmissionEvent.objects.create(submission=submission, action=SubmissionEvent.Action.SUBMITTED, actor_name="Customer", text=submission.message)
            return submission
        except IntegrityError:
            continue
    raise OperationError("Could not allocate a tracking code. Please try again.", "code_error")


def find_staff(identity, password):
    identity = identity.strip()
    if "@" in identity:
        staff = StaffMember.objects.select_related("user").filter(email__iexact=identity).first()
    else:
        staff = StaffMember.objects.select_related("user").filter(phone__in=phone_variants(identity)).first()
    if staff:
        user = authenticate(username=staff.user.username, password=password)
        if user and user.is_active:
            return user
    return None


def create_staff(data, creator):
    User = get_user_model()
    with transaction.atomic():
        user = User.objects.create_user(username=f"staff_{secrets.token_hex(12)}", email=data["email"].lower(), password=data["password"])
        user.first_name = data["full_name"][:150]
        user.is_staff = False
        user.save(update_fields=["first_name", "is_staff"])
        return StaffMember.objects.create(user=user, full_name=data["full_name"], email=data["email"].lower(), phone=normalize_phone(data["phone"]), created_by=creator)


def send_reset_otp(staff):
    now = timezone.now()
    code = f"{secrets.randbelow(1000000):06d}"
    reset = PasswordResetOTP.objects.create(staff=staff, code_hash=make_password(code), sent_at=now, expires_at=now + timedelta(minutes=10))
    try:
        send_mail("Your staff password reset code", f"Your one-time code is {code}. It expires in 10 minutes.", None, [staff.email], fail_silently=False)
    except Exception:
        reset.delete()
        raise
    PasswordResetOTP.objects.filter(staff=staff, consumed_at__isnull=True).exclude(pk=reset.pk).update(consumed_at=now)


def reset_password(email, code, new_password):
    staff = StaffMember.objects.select_related("user").filter(email__iexact=email.strip()).first()
    if not staff:
        return False
    with transaction.atomic():
        reset = PasswordResetOTP.objects.select_for_update().filter(staff=staff, consumed_at__isnull=True).order_by("-sent_at").first()
        if not reset or reset.expires_at <= timezone.now() or reset.attempts >= 5:
            return False
        reset.attempts += 1
        reset.save(update_fields=["attempts"])
        if not check_password(code, reset.code_hash):
            return False
        staff.user.set_password(new_password)
        staff.user.save(update_fields=["password"])
        reset.consumed_at = timezone.now()
        reset.save(update_fields=["consumed_at"])
        APIToken.objects.filter(staff=staff, revoked_at__isnull=True).update(revoked_at=timezone.now())
        return True


def issue_api_token(staff):
    raw = secrets.token_urlsafe(32)
    APIToken.objects.create(staff=staff, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now() + timedelta(days=30))
    return raw


def staff_from_token(raw):
    if not raw:
        return None
    digest = hashlib.sha256(raw.encode()).hexdigest()
    token = APIToken.objects.select_related("staff__user").filter(token_hash=digest, revoked_at__isnull=True, expires_at__gt=timezone.now()).first()
    return token.staff if token and token.staff.user.is_active else None


def reply_to_submission(submission, text, user=None, customer=False):
    with transaction.atomic():
        locked = Submission.objects.select_for_update().get(pk=submission.pk)
        if locked.archived_at:
            raise OperationError("This request is archived.", "archived_message")
        last = locked.events.filter(action__in=[SubmissionEvent.Action.STAFF_REPLY, SubmissionEvent.Action.CUSTOMER_REPLY]).order_by("-created_at", "-id").first()
        if customer:
            if not last or last.action != SubmissionEvent.Action.STAFF_REPLY:
                raise OperationError("There is no staff reply to respond to yet.", "no_staff_reply")
            action = SubmissionEvent.Action.CUSTOMER_REPLY
            name = locked.customer_name or "Customer"
        else:
            if last and last.action == SubmissionEvent.Action.STAFF_REPLY:
                raise OperationError("Wait for the customer to respond before replying again.", "reply_blocked")
            action = SubmissionEvent.Action.STAFF_REPLY
            name = staff_name(user)
        event = SubmissionEvent.objects.create(submission=locked, action=action, actor=user, actor_name=name, text=text.strip())
        if not customer and locked.status == Submission.Status.NEW:
            locked.status = Submission.Status.REVIEWING
            locked.save(update_fields=["status"])
        return event


def archive_submission(submission, user):
    with transaction.atomic():
        locked = Submission.objects.select_for_update().get(pk=submission.pk)
        if locked.archived_at:
            raise OperationError("This request is already archived.", "already_archived")
        locked.archived_at = timezone.now()
        locked.archived_by = user
        locked.status = Submission.Status.CLOSED
        locked.save(update_fields=["archived_at", "archived_by", "status"])
        return SubmissionEvent.objects.create(submission=locked, action=SubmissionEvent.Action.ARCHIVED, actor=user, actor_name=staff_name(user))
