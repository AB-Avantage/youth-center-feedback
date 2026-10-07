import secrets

from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    Submission = apps.get_model("feedback", "Submission")
    SubmissionEvent = apps.get_model("feedback", "SubmissionEvent")
    used = set(Submission.objects.exclude(tracking_code__isnull=True).values_list("tracking_code", flat=True))
    for submission in Submission.objects.filter(tracking_code__isnull=True).iterator():
        while True:
            code = f"{secrets.randbelow(90000000) + 10000000:08d}"
            if code not in used:
                break
        used.add(code)
        submission.tracking_code = code
        if submission.status == "closed":
            submission.archived_at = submission.created_at or timezone.now()
        submission.save(update_fields=["tracking_code", "archived_at"])
        SubmissionEvent.objects.create(submission=submission, action="submitted", actor_name="Customer", text=submission.message)


class Migration(migrations.Migration):
    dependencies = [("feedback", "0003_ratelimitbucket_submission_archived_at_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
