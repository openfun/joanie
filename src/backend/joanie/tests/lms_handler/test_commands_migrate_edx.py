"""Test suite for the management command `synchronize_course_runs`."""
from dataclasses import dataclass
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings

import factory
import responses

from joanie.core import factories, models, utils
from joanie.lms_handler.management.commands.migrate_edx import (
    EDX_DOMAIN,
    make_date_aware,
)

LOGO_NAME = "creative_common.jpeg"
with open(join(dirname(realpath(__file__)), f"images/{LOGO_NAME}"), "rb") as logo:
    LOGO_CONTENT = logo.read()


@dataclass
class EdxUniversity:
    name: str
    code: str
    logo: str


class EdxUniversityFactory(factory.Factory):
    class Meta:
        model = EdxUniversity

    name = factory.Faker("company")
    code = factory.Faker("pystr", max_chars=10)
    logo = factory.Faker("file_name")


@dataclass
class EdxCourseOverview:
    id: str
    start: str
    end: str
    enrollment_start: str
    enrollment_end: str
    created: str
    display_name: str


class EdxCourseOverviewFactory(factory.Factory):
    class Meta:
        model = EdxCourseOverview

    id = factory.Faker("pystr", max_chars=10)
    start = factory.Faker("date_time")
    end = factory.Faker("date_time")
    enrollment_start = factory.Faker("date_time")
    enrollment_end = factory.Faker("date_time")
    created = factory.Faker("date_time")
    display_name = factory.Faker("sentence")


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    },
)
class MigrateOpenEdxTestCase(TestCase):
    """Test case for the management command `migrate_edx`."""

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_universities"
    )
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_create(self, mock_get_universities):
        edx_universities = EdxUniversityFactory.create_batch(10)
        mock_get_universities.return_value = edx_universities

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        call_command("migrate_edx", "--universities")

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_universities"
    )
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_update(self, mock_get_universities):
        organization = factories.OrganizationFactory.create(
            code="orga",
            title="Organization 1 old title",
            logo=None,
        )
        edx_universities = [
            EdxUniversityFactory.create(
                code=organization.code,
                name="Organization 1",
                logo="logo.png",
            )
        ]
        mock_get_universities.return_value = edx_universities

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        call_command("migrate_edx", "--universities")

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_runs_create(self, mock_get_course_overviews):
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(10)
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_run in edx_course_overviews:
            course = models.Course.objects.get(
                code=utils.normalize_code(edx_course_run.id)
            )
            self.assertEqual(course.title, edx_course_run.display_name)
            self.assertEqual(course.created_on, make_date_aware(edx_course_run.created))
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language("fr")
            self.assertEqual(course_run.title, edx_course_run.display_name)
            self.assertEqual(course_run.start, make_date_aware(edx_course_run.start))
            self.assertEqual(course_run.end, make_date_aware(edx_course_run.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_run.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_run.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])
