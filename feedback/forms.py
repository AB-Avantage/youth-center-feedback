from django import forms
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.utils import translation
from django.utils.translation import get_language

from .models import StaffMember, Submission
from .services import normalize_phone, phone_variants
from .texts import TEXTS


class SubmissionForm(forms.Form):
    facility = forms.ChoiceField()
    category = forms.ChoiceField()
    name = forms.CharField(max_length=255, required=False)
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}))
    email = forms.EmailField(required=False)
    message = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={"rows": 7}))

    def __init__(self, *args, facilities, language="ar", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        copy = TEXTS[language]
        self.facilities = {str(facility.id): facility for facility in facilities}
        self.fields["facility"].label = copy["facility"]
        self.fields["facility"].choices = [("", copy["choose_facility"])] + [(str(facility.id), facility.label(language)) for facility in facilities]
        self.fields["category"].label = copy["category"]
        self.fields["category"].choices = [("", copy["choose_category"]), (Submission.Category.REPORT, copy["report"]), (Submission.Category.RECOMMENDATION, copy["recommendation"])]
        for name in ("name", "phone", "email", "message"):
            self.fields[name].label = copy[name]
        for field in self.fields.values():
            field.error_messages["required"] = copy["required_error"]
            field.error_messages["max_length"] = copy["max_length_error"]
        self.fields["email"].error_messages["invalid"] = copy["invalid_email"]
        for name in ("facility", "category"):
            self.fields[name].error_messages["invalid_choice"] = copy["invalid_choice_error"]

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if phone and (not phone.lstrip("+").isdigit() or not 7 <= len(phone.lstrip("+")) <= 15):
            raise forms.ValidationError(TEXTS[self.language]["invalid_phone"])
        return phone

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if not message:
            raise forms.ValidationError(TEXTS[self.language]["empty_message"])
        return message


class LocalizedForm(forms.Form):
    def __init__(self, *args, language="en", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        for field in self.fields.values():
            field.error_messages["required"] = TEXTS[language]["required_error"]
            field.error_messages["invalid"] = TEXTS[language]["invalid_value"]


class TrackingForm(LocalizedForm):
    code = forms.RegexField(regex=r"^[0-9]{8}$", max_length=8)


class ReplyForm(LocalizedForm):
    text = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={"rows": 5}))


class StaffLoginForm(LocalizedForm):
    identity = forms.CharField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)


class StaffCreateForm(LocalizedForm):
    full_name = forms.CharField(max_length=255)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if StaffMember.objects.filter(email__iexact=email).exists():
            raise ValidationError(TEXTS[self.language]["staff_duplicate"])
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not phone.lstrip("+").isdigit() or not 7 <= len(phone.lstrip("+")) <= 15:
            raise ValidationError(TEXTS[self.language]["invalid_phone"])
        if StaffMember.objects.filter(phone__in=phone_variants(phone)).exists():
            raise ValidationError(TEXTS[self.language]["staff_duplicate"])
        return phone

    def clean_password(self):
        password = self.cleaned_data["password"]
        with translation.override(self.language):
            validate_password(password)
        return password


class StaffPortalUserFields(forms.Form):
    portal_staff = forms.BooleanField(required=False)
    staff_phone = forms.CharField(max_length=20, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = "ar" if (get_language() or "en").startswith("ar") else "en"
        copy = TEXTS[language]
        self.fields["portal_staff"].label = copy["portal_staff_checkbox"]
        self.fields["portal_staff"].help_text = copy["portal_staff_help"]
        self.fields["staff_phone"].label = copy["staff_phone"]
        user = getattr(self, "instance", None)
        if user and user.pk:
            profile = StaffMember.objects.filter(user=user).first()
            self.fields["portal_staff"].initial = bool(profile)
            self.fields["staff_phone"].initial = profile.phone if profile else ""

    def clean(self):
        data = super().clean()
        if not data.get("portal_staff"):
            return data
        language = "ar" if (get_language() or "en").startswith("ar") else "en"
        copy = TEXTS[language]
        if data.get("is_superuser") or (getattr(self, "instance", None) and self.instance.is_superuser):
            self.add_error("portal_staff", copy["portal_staff_admin_error"])
        if not data.get("email"):
            self.add_error("email", copy["required_error"])
        if not (data.get("first_name") or data.get("last_name")):
            self.add_error("first_name", copy["required_error"])
        phone = normalize_phone(data.get("staff_phone", ""))
        if not phone:
            self.add_error("staff_phone", copy["required_error"])
        elif not phone.lstrip("+").isdigit() or not 7 <= len(phone.lstrip("+")) <= 15:
            self.add_error("staff_phone", copy["invalid_phone"])
        else:
            data["staff_phone"] = phone
            other_staff = StaffMember.objects.filter(phone__in=phone_variants(phone))
            if getattr(self, "instance", None) and self.instance.pk:
                other_staff = other_staff.exclude(user=self.instance)
            if other_staff.exists():
                self.add_error("staff_phone", copy["staff_duplicate"])
        email = (data.get("email") or "").strip().lower()
        if email:
            data["email"] = email
            other_staff = StaffMember.objects.filter(email__iexact=email)
            if getattr(self, "instance", None) and self.instance.pk:
                other_staff = other_staff.exclude(user=self.instance)
            if other_staff.exists():
                self.add_error("email", copy["staff_duplicate"])
        return data


class FeedbackAdminUserAddForm(StaffPortalUserFields, AdminUserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)


class FeedbackAdminUserChangeForm(StaffPortalUserFields, UserChangeForm):
    pass


class OTPRequestForm(LocalizedForm):
    email = forms.EmailField()


class PasswordResetForm(LocalizedForm):
    email = forms.EmailField()
    code = forms.RegexField(regex=r"^[0-9]{6}$", max_length=6)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password") and data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", TEXTS[self.language]["password_mismatch"])
        if data.get("password"):
            try:
                with translation.override(self.language):
                    validate_password(data["password"])
            except ValidationError as exc:
                self.add_error("password", exc)
        return data
