# Generated by Django 3.2.20 on 2023-10-25 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0021_auto_20230805_1740'),
    ]

    operations = [
        migrations.AddField(
            model_name='amazonpurchase',
            name='metadata',
            field=models.TextField(blank=True, max_length=4194304, null=True),
        ),
    ]
