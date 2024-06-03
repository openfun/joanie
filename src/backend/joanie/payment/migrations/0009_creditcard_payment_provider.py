# Generated by Django 4.2.13 on 2024-06-03 08:56

from django.db import migrations, models

from joanie.payment import get_payment_backend


def update_payment_provider_field(apps, schema_editor):
    """
    We are adding a new field `payment_provider` on the `CreditCard` model that contains the
    information on the payment provider that tokenized the card. This method updates every existing
    `CreditCard` instances in the database with the name of the active payment provider as
    specified into the settings.
    """
    CreditCard = apps.get_model('payment', 'CreditCard')
    payment_backend = get_payment_backend()
    CreditCard.objects.update(payment_provider=payment_backend.name)


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0008_creditcard_initial_issuer_transaction_identifier'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditcard',
            name='payment_provider',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='payment provider'),
        ),
        migrations.RunPython(update_payment_provider_field, migrations.RunPython.noop)
    ]
