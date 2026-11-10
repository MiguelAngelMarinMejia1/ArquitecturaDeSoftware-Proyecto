from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0003_roomtype_image"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="roomtype",
            name="image",
        ),
        migrations.RemoveField(
            model_name="roomtype",
            name="image_url",
        ),
        migrations.AddField(
            model_name="room",
            name="image_urls",
            field=models.TextField(
                blank=True,
                help_text="URLs separadas por comas, en el orden de la galeria.",
                verbose_name="URLs de imagenes",
            ),
        ),
    ]
