# Generated by Django 4.2.19 on 2025-02-12 16:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0054_discount_discount_discount_rate_or_amount_required_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='documentimage',
            options={'ordering': ['created_on']},
        ),
        migrations.AlterModelOptions(
            name='ordergroup',
            options={'ordering': ['created_on']},
        ),
    ]
