# pylint: skip-file
# Generated by Django 3.2.20 on 2024-01-31 01:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0023_amazonasinitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='amazonasinitem',
            name='item_name',
            field=models.CharField(blank=True, default='Unknown Item', max_length=4096, null=True),
        ),
    ]
