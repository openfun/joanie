# Generated by Django 4.2.10 on 2024-02-16 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_order_has_consent_to_terms'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='effort',
            field=models.DurationField(blank=True, help_text='The duration effort required in seconds', null=True, verbose_name='Effort in seconds'),
        ),
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=40, null=True, verbose_name='Phone number'),
        ),
    ]
