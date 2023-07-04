# Generated by Django 4.2.2 on 2023-07-04 17:22

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import joanie.core.fields.multiselect


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_courseproductrelation_add_max_validated_orders"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseWish",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="primary key for the record as UUID",
                        primary_key=True,
                        serialize=False,
                        verbose_name="id",
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="date and time at which a record was created",
                        verbose_name="created on",
                    ),
                ),
                (
                    "updated_on",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="date and time at which a record was last updated",
                        verbose_name="updated on",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Wish",
                "verbose_name_plural": "Course Wishes",
                "db_table": "joanie_course_wish",
            },
        ),
        migrations.AlterModelOptions(
            name="certificatedefinition",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Certificate definition",
                "verbose_name_plural": "Certificate definitions",
            },
        ),
        migrations.AlterModelOptions(
            name="courseaccess",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Course access",
                "verbose_name_plural": "Course accesses",
            },
        ),
        migrations.AlterModelOptions(
            name="courseproductrelation",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Course relation to a product",
                "verbose_name_plural": "Courses relations to products",
            },
        ),
        migrations.AlterModelOptions(
            name="courserun",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Course run",
                "verbose_name_plural": "Course runs",
            },
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
            },
        ),
        migrations.AlterModelOptions(
            name="organizationaccess",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Organization access",
                "verbose_name_plural": "Organization accesses",
            },
        ),
        migrations.AlterModelOptions(
            name="product",
            options={
                "ordering": ["-created_on"],
                "verbose_name": "Product",
                "verbose_name_plural": "Products",
            },
        ),
        migrations.RemoveConstraint(
            model_name="order",
            name="unique_owner_product_not_canceled",
        ),
        migrations.AlterField(
            model_name="courserun",
            name="languages",
            field=joanie.core.fields.multiselect.MultiSelectField(
                choices=[
                    ("af", "Afrikaans"),
                    ("ar", "Arabic"),
                    ("ar-dz", "Algerian Arabic"),
                    ("ast", "Asturian"),
                    ("az", "Azerbaijani"),
                    ("bg", "Bulgarian"),
                    ("be", "Belarusian"),
                    ("bn", "Bengali"),
                    ("br", "Breton"),
                    ("bs", "Bosnian"),
                    ("ca", "Catalan"),
                    ("ckb", "Central Kurdish (Sorani)"),
                    ("cs", "Czech"),
                    ("cy", "Welsh"),
                    ("da", "Danish"),
                    ("de", "German"),
                    ("dsb", "Lower Sorbian"),
                    ("el", "Greek"),
                    ("en", "English"),
                    ("en-au", "Australian English"),
                    ("en-gb", "British English"),
                    ("eo", "Esperanto"),
                    ("es", "Spanish"),
                    ("es-ar", "Argentinian Spanish"),
                    ("es-co", "Colombian Spanish"),
                    ("es-mx", "Mexican Spanish"),
                    ("es-ni", "Nicaraguan Spanish"),
                    ("es-ve", "Venezuelan Spanish"),
                    ("et", "Estonian"),
                    ("eu", "Basque"),
                    ("fa", "Persian"),
                    ("fi", "Finnish"),
                    ("fr", "French"),
                    ("fy", "Frisian"),
                    ("ga", "Irish"),
                    ("gd", "Scottish Gaelic"),
                    ("gl", "Galician"),
                    ("he", "Hebrew"),
                    ("hi", "Hindi"),
                    ("hr", "Croatian"),
                    ("hsb", "Upper Sorbian"),
                    ("hu", "Hungarian"),
                    ("hy", "Armenian"),
                    ("ia", "Interlingua"),
                    ("id", "Indonesian"),
                    ("ig", "Igbo"),
                    ("io", "Ido"),
                    ("is", "Icelandic"),
                    ("it", "Italian"),
                    ("ja", "Japanese"),
                    ("ka", "Georgian"),
                    ("kab", "Kabyle"),
                    ("kk", "Kazakh"),
                    ("km", "Khmer"),
                    ("kn", "Kannada"),
                    ("ko", "Korean"),
                    ("ky", "Kyrgyz"),
                    ("lb", "Luxembourgish"),
                    ("lt", "Lithuanian"),
                    ("lv", "Latvian"),
                    ("mk", "Macedonian"),
                    ("ml", "Malayalam"),
                    ("mn", "Mongolian"),
                    ("mr", "Marathi"),
                    ("ms", "Malay"),
                    ("my", "Burmese"),
                    ("nb", "Norwegian Bokmål"),
                    ("ne", "Nepali"),
                    ("nl", "Dutch"),
                    ("nn", "Norwegian Nynorsk"),
                    ("os", "Ossetic"),
                    ("pa", "Punjabi"),
                    ("pl", "Polish"),
                    ("pt", "Portuguese"),
                    ("pt-br", "Brazilian Portuguese"),
                    ("ro", "Romanian"),
                    ("ru", "Russian"),
                    ("sk", "Slovak"),
                    ("sl", "Slovenian"),
                    ("sq", "Albanian"),
                    ("sr", "Serbian"),
                    ("sr-latn", "Serbian Latin"),
                    ("sv", "Swedish"),
                    ("sw", "Swahili"),
                    ("ta", "Tamil"),
                    ("te", "Telugu"),
                    ("tg", "Tajik"),
                    ("th", "Thai"),
                    ("tk", "Turkmen"),
                    ("tr", "Turkish"),
                    ("tt", "Tatar"),
                    ("udm", "Udmurt"),
                    ("uk", "Ukrainian"),
                    ("ur", "Urdu"),
                    ("uz", "Uzbek"),
                    ("vi", "Vietnamese"),
                    ("zh-hans", "Simplified Chinese"),
                    ("zh-hant", "Traditional Chinese"),
                ],
                help_text="The list of languages in which the course content is available.",
                max_choices=50,
                max_length=255,
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                condition=models.Q(("state", "canceled"), _negated=True),
                fields=("course", "owner", "product"),
                name="unique_owner_product_not_canceled",
                violation_error_message="An order for this product and course already exists.",
            ),
        ),
        migrations.AddField(
            model_name="coursewish",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="wishes",
                to="core.course",
                verbose_name="Course",
            ),
        ),
        migrations.AddField(
            model_name="coursewish",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="course_wishes",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Owner",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="coursewish",
            unique_together={("owner", "course")},
        ),
    ]
