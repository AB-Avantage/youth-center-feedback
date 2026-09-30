from django import forms

from .models import Submission
from .services import normalize_phone
from .texts import TEXTS


class SubmissionForm(forms.Form):
    facility = forms.ChoiceField()
    category = forms.ChoiceField()
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}))
    message = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={"rows": 7}))

    def __init__(self, *args, facilities, language="ar", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        copy = TEXTS[language]
        self.facilities = {str(facility.id): facility for facility in facilities}
        self.fields["facility"].label = copy["facility"]
        self.fields["facility"].choices = [("", copy["choose_facility"])] + [
            (str(facility.id), facility.label(language)) for facility in facilities
        ]
        self.fields["category"].label = copy["category"]
        self.fields["category"].choices = [
            ("", copy["choose_category"]),
            (Submission.Category.REPORT, copy["report"]),
            (Submission.Category.RECOMMENDATION, copy["recommendation"]),
        ]
        self.fields["phone"].label = copy["phone"]
        self.fields["message"].label = copy["message"]

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not phone or not phone.lstrip("+").isdigit() or not 7 <= len(phone.lstrip("+")) <= 15:
            raise forms.ValidationError(TEXTS[self.language]["invalid_phone"])
        return phone

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if not message:
            raise forms.ValidationError(TEXTS[self.language]["empty_message"])
        return message
