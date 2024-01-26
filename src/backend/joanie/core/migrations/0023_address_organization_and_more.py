# Generated by Django 4.2.9 on 2024-01-31 10:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_contract_reference_datetime_not_both_set_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to='core.organization', verbose_name='organization'),
        ),
        migrations.AddField(
            model_name='organization',
            name='activity_category_code',
            field=models.CharField(blank=True, max_length=50, verbose_name='Activity category code'),
        ),
        migrations.AddField(
            model_name='organization',
            name='contact_email',
            field=models.CharField(blank=True, max_length=100, verbose_name='Contact email'),
        ),
        migrations.AddField(
            model_name='organization',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=40, verbose_name='Contact phone number'),
        ),
        migrations.AddField(
            model_name='organization',
            name='dpo_email',
            field=models.CharField(blank=True, max_length=100, verbose_name='Data protection officer email'),
        ),
        migrations.AddField(
            model_name='organization',
            name='enterprise_code',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Enterprise code'),
        ),
        migrations.AddField(
            model_name='organization',
            name='representative_profession',
            field=models.CharField(blank=True, help_text='representative profession', max_length=100, null=True, verbose_name="Profession of the organization's representative"),
        ),
        migrations.AddField(
            model_name='organization',
            name='signatory_representative',
            field=models.CharField(blank=True, help_text="This field is optional. If it is set, you must set the field'signatory_representative_profession' as well", max_length=100, null=True, verbose_name='Signatory representative'),
        ),
        migrations.AddField(
            model_name='organization',
            name='signatory_representative_profession',
            field=models.CharField(blank=True, help_text='signatory representative profession', max_length=100, null=True, verbose_name='Profession of the signatory representative'),
        ),
        migrations.AlterField(
            model_name='address',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to=settings.AUTH_USER_MODEL, verbose_name='owner'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='country',
            field=django_countries.fields.CountryField(default='FR', help_text='Country field will be deprecated soon in order to be replaced by address relation.', max_length=2, verbose_name='country'),
        ),
        migrations.AddConstraint(
            model_name='address',
            constraint=models.UniqueConstraint(condition=models.Q(('is_main', True)), fields=('organization',), name='unique_main_address_per_organization'),
        ),
        migrations.AddConstraint(
            model_name='address',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('organization__isnull', False), ('owner__isnull', True)), models.Q(('organization__isnull', True), ('owner__isnull', False)), _connector='OR'), name='either_owner_or_organization', violation_error_message='Either owner or organization must be set.'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('signatory_representative__isnull', False), ('signatory_representative_profession__isnull', False)), models.Q(('signatory_representative__isnull', True), ('signatory_representative_profession__isnull', True)), _connector='OR'), name='both_signatory_representative_fields_must_be_set', violation_error_message='Both signatory representative fields must be set.'),
        ),
    ]
