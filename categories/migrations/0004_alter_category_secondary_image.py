# /categories/migrations/0004_alter_category_secondary_image.py

import categories.models
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_category_secondary_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='secondary_image',
            field=models.ImageField(
                upload_to='category_images/',
                validators=[categories.models.validate_image],
                blank=True,
                null=True,
            ),
        ),
    ]
