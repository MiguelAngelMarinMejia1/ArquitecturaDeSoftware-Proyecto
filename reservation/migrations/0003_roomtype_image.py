from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0002_roomtype_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="roomtype",
            name="image",
            field=models.ImageField(
                blank=True,
                upload_to="room-types/",
                verbose_name="archivo de imagen",
            ),
        ),
    ]
