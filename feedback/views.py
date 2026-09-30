from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SubmissionForm
from .models import Submission
from .services import EZYXSUnavailable, active_facilities, find_customer_by_phone
from .texts import TEXTS


def page_context(language, **extra):
    return {
        "language": language,
        "copy": TEXTS[language],
        "switch_url": "submission_create_en" if language == "ar" else "submission_create_ar",
        **extra,
    }


@require_http_methods(["GET", "POST"])
def submission_create(request, language):
    try:
        facilities = active_facilities()
    except EZYXSUnavailable:
        return render(request, "feedback/unavailable.html", page_context(language), status=503)

    form = SubmissionForm(request.POST or None, facilities=facilities, language=language)
    if request.method == "POST" and form.is_valid():
        try:
            customer = find_customer_by_phone(form.cleaned_data["phone"])
        except EZYXSUnavailable:
            customer = None
        facility = form.facilities[form.cleaned_data["facility"]]
        submission = Submission.objects.create(
            facility_id=facility.id,
            facility_name=facility.label("en"),
            category=form.cleaned_data["category"],
            message=form.cleaned_data["message"],
            customer_id=customer.id if customer else None,
            customer_name=customer.name if customer else "",
            customer_phone=customer.phone if customer else form.cleaned_data["phone"],
            customer_email=customer.email or "" if customer else "",
        )
        return redirect("submission_success_" + language, pk=submission.pk)
    return render(request, "feedback/form.html", page_context(language, form=form))


def submission_success(request, pk, language):
    # A public reference number is deliberately not a way to read submissions.
    if pk < 1:
        raise Http404
    return render(request, "feedback/success.html", page_context(language, reference=pk))
