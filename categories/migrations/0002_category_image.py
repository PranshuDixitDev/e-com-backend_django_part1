# /categories/migrations/0002_category_image.py

import categories.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.ImageField(
                upload_to='category_images/',
                validators=[categories.models.validate_image],
                blank=False,
                null=False,
            ),
        ),
    ]
