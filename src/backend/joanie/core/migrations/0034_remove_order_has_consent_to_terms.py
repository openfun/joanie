# Generated by Django 4.2.13 on 2024-06-05 10:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_alter_order_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='has_consent_to_terms',
        ),
    ]
