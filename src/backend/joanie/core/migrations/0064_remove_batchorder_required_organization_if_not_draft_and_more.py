# Generated by Django 4.2.20 on 2025-04-25 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_batchorder_state_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='batchorder',
            name='required_organization_if_not_draft',
        ),
        migrations.AlterField(
            model_name='batchorder',
            name='state',
            field=models.CharField(choices=[('draft', 'Draft'), ('assigned', 'Assigned'), ('to_sign', 'To sign'), ('signing', 'Signing'), ('pending', 'Pending'), ('failed_payment', 'Failed payment'), ('canceled', 'Canceled'), ('completed', 'Completed')], db_index=True, default='draft'),
        ),
        migrations.AddConstraint(
            model_name='batchorder',
            constraint=models.CheckConstraint(check=models.Q(('state__in', ['draft', 'canceled']), ('organization__isnull', False), _connector='OR'), name='required_organization_if_not_draft_or_canceled', violation_error_message='BatchOrder requires organization unless in draft or cancel states.'),
        ),
    ]
