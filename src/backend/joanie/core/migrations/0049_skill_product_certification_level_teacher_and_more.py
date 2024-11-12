# Generated by Django 4.2.16 on 2024-12-03 16:29

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import parler.fields
import parler.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_alter_order_payment_schedule'),
    ]

    operations = [
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='primary key for the record as UUID', primary_key=True, serialize=False, verbose_name='id')),
                ('created_on', models.DateTimeField(auto_now_add=True, help_text='date and time at which a record was created', verbose_name='created on')),
                ('updated_on', models.DateTimeField(auto_now=True, help_text='date and time at which a record was last updated', verbose_name='updated on')),
            ],
            options={
                'verbose_name': 'Skill',
                'verbose_name_plural': 'Skills',
                'db_table': 'joanie_skill',
                'ordering': ['created_on'],
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.AddField(
            model_name='product',
            name='certification_level',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Level of certification as defined by the European Qualifications Framework.', null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(8)], verbose_name='level of certification'),
        ),
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='primary key for the record as UUID', primary_key=True, serialize=False, verbose_name='id')),
                ('created_on', models.DateTimeField(auto_now_add=True, help_text='date and time at which a record was created', verbose_name='created on')),
                ('updated_on', models.DateTimeField(auto_now=True, help_text='date and time at which a record was last updated', verbose_name='updated on')),
                ('first_name', models.CharField(max_length=255, verbose_name='first name')),
                ('last_name', models.CharField(max_length=255, verbose_name='last name')),
            ],
            options={
                'verbose_name': 'Teacher',
                'verbose_name_plural': 'Teachers',
                'db_table': 'joanie_teacher',
                'ordering': ['last_name', 'first_name'],
                'unique_together': {('first_name', 'last_name')},
            },
        ),
        migrations.AddField(
            model_name='product',
            name='skills',
            field=models.ManyToManyField(blank=True, help_text='Skills that will be displayed on the delivered certificate.', related_name='products', to='core.skill', verbose_name='skills'),
        ),
        migrations.AddField(
            model_name='product',
            name='teachers',
            field=models.ManyToManyField(blank=True, help_text='Teachers that will be displayed on the delivered certificate.', related_name='products', to='core.teacher', verbose_name='teachers'),
        ),
        migrations.CreateModel(
            name='SkillTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language_code', models.CharField(db_index=True, max_length=15, verbose_name='Language')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('master', parler.fields.TranslationsForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='core.skill')),
            ],
            options={
                'verbose_name': 'Skill Translation',
                'db_table': 'joanie_skill_translation',
                'db_tablespace': '',
                'managed': True,
                'default_permissions': (),
                'unique_together': {('language_code', 'master')},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
    ]
