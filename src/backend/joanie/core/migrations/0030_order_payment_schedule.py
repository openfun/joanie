# Generated by Django 4.2.11 on 2024-04-05 09:05

from django.db import migrations, models
import joanie.core.fields.schedule


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_user_has_subscribed_to_commercial_newsletter'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_schedule',
            field=models.JSONField(blank=True, editable=False, encoder=joanie.core.fields.schedule.OrderPaymentScheduleEncoder, help_text='Payment schedule for the order.', null=True, verbose_name='payment schedule'),
        ),
    ]
