# Generated by Django 5.0.6 on 2024-09-14 15:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_alter_category_secondary_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='category_id',
        ),
    ]
