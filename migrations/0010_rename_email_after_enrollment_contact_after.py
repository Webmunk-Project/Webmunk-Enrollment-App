# pylint: skip-file
# Generated by Django 3.2.13 on 2022-07-06 13:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0009_enrollment_email_after'),
    ]

    operations = [
        migrations.RenameField(
            model_name='enrollment',
            old_name='email_after',
            new_name='contact_after',
        ),
    ]