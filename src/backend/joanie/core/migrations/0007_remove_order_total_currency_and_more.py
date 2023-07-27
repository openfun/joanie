# Generated by Django 4.2.2 on 2023-07-26 15:08

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_add_coursewish"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="order",
            name="total_currency",
        ),
        migrations.RemoveField(
            model_name="product",
            name="price_currency",
        ),
        migrations.AlterField(
            model_name="order",
            name="total",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0.0,
                editable=False,
                help_text="tax included",
                max_digits=9,
                validators=[django.core.validators.MinValueValidator(0.0)],
                verbose_name="price",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0.0,
                help_text="tax included",
                max_digits=9,
                validators=[django.core.validators.MinValueValidator(0.0)],
                verbose_name="price",
            ),
        ),
    ]
