from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("feedback", "0004_backfill_tracking_codes")]
    operations = [
        migrations.AlterField(
            model_name="submission",
            name="tracking_code",
            field=models.CharField(max_length=8, unique=True),
        ),
    ]
