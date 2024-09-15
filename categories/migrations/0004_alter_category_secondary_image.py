# Generated by Django 5.0.6 on 2024-09-14 11:33

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
            field=models.ImageField(blank=True, default=categories.models.get_placeholder_image, null=True, upload_to='category_images/', validators=[categories.models.validate_image]),
        ),
    ]