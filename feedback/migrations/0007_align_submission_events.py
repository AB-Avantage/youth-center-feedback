from django.db import migrations


def align_created_at(apps, schema_editor):
    SubmissionEvent = apps.get_model("feedback", "SubmissionEvent")
    for event in SubmissionEvent.objects.filter(action="submitted").select_related("submission").iterator():
        if event.created_at != event.submission.created_at:
            SubmissionEvent.objects.filter(pk=event.pk).update(created_at=event.submission.created_at)


class Migration(migrations.Migration):
    dependencies = [("feedback", "0006_alter_submissionevent_action")]
    operations = [migrations.RunPython(align_created_at, migrations.RunPython.noop)]
