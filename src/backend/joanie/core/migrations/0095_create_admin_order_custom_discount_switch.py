from django.db import migrations

SWITCH_NAME = "admin_order_custom_discount"
SWITCH_NOTE = (
    "Toggle the custom discount option on the admin order creation form."
)


def create_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.update_or_create(
        name=SWITCH_NAME,
        defaults={"active": False, "note": SWITCH_NOTE},
    )


def delete_switch(apps, schema_editor):
    Switch = apps.get_model("waffle", "Switch")
    Switch.objects.filter(name=SWITCH_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0094_order_nature"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(create_switch, delete_switch),
    ]
