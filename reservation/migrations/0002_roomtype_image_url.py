from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="roomtype",
            name="image_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                verbose_name="imagen",
            ),
        ),
    ]
