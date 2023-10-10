# Generated by Django 4.2.5 on 2023-10-04 13:21

import django.db.models.deletion
from django.db import migrations, models

from joanie.core import enums


def forwards_func(apps, schema_editor):
    """
    Update the template field value of all CertificateDefinition objects that used
    the "howard.issuers.CertificateDocument" template to "degree".
    """
    CertificateDefinition = apps.get_model("core", "CertificateDefinition")

    definitions = CertificateDefinition.objects.filter(
        template="howard.issuers.CertificateDocument"
    )

    for definition in definitions:
        definition.template = enums.DEGREE

    CertificateDefinition.objects.bulk_update(definitions, ["template"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_contractdefinition_contract_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="certificatedefinition",
            name="template",
            field=models.CharField(
                blank=True,
                choices=[("certificate", "Certificate"), ("degree", "Degree")],
                max_length=255,
                null=True,
                verbose_name="template to generate pdf",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="contract_definition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="core.contractdefinition",
                verbose_name="Contract definition",
            ),
        ),
        migrations.RunPython(forwards_func),
    ]
