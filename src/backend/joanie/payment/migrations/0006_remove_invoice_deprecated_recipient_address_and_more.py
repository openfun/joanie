# Generated by Django 4.2.7 on 2023-11-23 15:45
from typing import Tuple

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payment", "0005_invoice_recipient_address")]

    operations = [
        migrations.RemoveField(
            model_name="invoice",
            name="deprecated_recipient_address",
        ),
        migrations.RemoveField(
            model_name="invoice",
            name="deprecated_recipient_name",
        ),
        migrations.AlterField(
            model_name="invoice",
            name="recipient_address",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="invoices",
                to="core.address",
                verbose_name="invoice address",
            ),
        ),
    ]
