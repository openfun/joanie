# Generated by Django 4.2.5 on 2023-09-20 08:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_remove_courseproductrelation_max_validated_orders_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="producttranslation",
            name="instructions",
            field=models.TextField(blank=True, verbose_name="instructions"),
        ),
    ]
