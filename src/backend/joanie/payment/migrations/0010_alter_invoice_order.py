# Generated by Django 4.2.15 on 2024-08-22 14:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_alter_enrollment_user_alter_order_owner'),
        ('payment', '0009_creditcard_payment_provider'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='core.order', verbose_name='order'),
        ),
    ]
