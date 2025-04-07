# Generated by Django 4.2.19 on 2025-03-31 17:04

from django.db import migrations, models
import joanie.core.models.products


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0061_alter_discount_amount_alter_discount_rate'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='voucher',
            name='unique_code_order_group',
        ),
        migrations.AlterField(
            model_name='voucher',
            name='code',
            field=models.CharField(default=joanie.core.models.products.generate_random_code, help_text='Voucher code', max_length=255, unique=True, verbose_name='code'),
        ),
    ]
