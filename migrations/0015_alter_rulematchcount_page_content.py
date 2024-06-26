# pylint: skip-file
# Generated by Django 3.2.14 on 2022-08-10 17:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0014_remove_rulematchcount_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rulematchcount',
            name='page_content',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rule_matches', to='enrollment.pagecontent'),
        ),
    ]
