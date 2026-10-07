from .texts import TEXTS


def portal_copy(request):
    language = "ar" if getattr(request, "LANGUAGE_CODE", "en") == "ar" else "en"
    return {"portal_copy": TEXTS[language]}
