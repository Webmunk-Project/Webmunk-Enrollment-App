# pylint: skip-file
# Generated by Django 3.2.11 on 2022-01-19 13:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtensionRuleSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1024)),
                ('is_active', models.BooleanField(default=True)),
                ('rule_json', models.TextField(default='[]', max_length=16777216)),
            ],
        ),
        migrations.AddField(
            model_name='enrollment',
            name='rule_set',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='enrollments', to='enrollment.extensionruleset'),
        ),
    ]
