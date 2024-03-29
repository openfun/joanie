# Generated by Django 4.2.7 on 2023-11-23 15:33

from django.db import migrations, models


def default_is_reusable_true(apps, schema_editor):
    """
    The new Address field `is_reusable` defaults to False,
    but we want it to be True for all pre-existing objects.
    """
    Address = apps.get_model("core", "Address")
    Address.objects.update(is_reusable=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_alter_ordergroup_course_product_relation"),
    ]

    operations = [
        migrations.AddField(
            model_name="address",
            name="is_reusable",
            field=models.BooleanField(default=False, verbose_name="reusable"),
        ),
        migrations.RunPython(default_is_reusable_true, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("is_reusable", True), ("is_main", False), _connector="OR"
                ),
                name="main_address_must_be_reusable",
                violation_error_message="Main address must be reusable.",
            ),
        ),
    ]
