"""Tests for the import_universities task."""

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
import os
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

import responses

from joanie.core import factories, models, utils
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks.universities import import_universities

LOGO_NAME = "creative_common.jpeg"
with open(join(dirname(realpath(__file__)), f"images/{LOGO_NAME}"), "rb") as logo:
    LOGO_CONTENT = logo.read()


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": os.path.join(settings.MEDIA_ROOT, "tests"),
                "base_url": "/media/tests/",
            },
        }
    },
    JOANIE_LMS_BACKENDS=[
        {
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        }
    ],
    EDX_DATABASE_USER="test",
    EDX_DATABASE_PASSWORD="test",
    EDX_DATABASE_HOST="test",
    EDX_DATABASE_PORT="1234",
    EDX_DATABASE_NAME="test",
    EDX_DOMAIN="openedx.test",
    EDX_TIME_ZONE="UTC",
    TIME_ZONE="UTC",
)
class EdxImportUniversitiesTestCase(TestCase):
    """Tests for the import_universities task."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        edx_factories.session.rollback()

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_create(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that universities are created from the edx universities and that their
        logos are downloaded.
        """
        edx_universities = edx_factories.EdxUniversityFactory.create_batch(10)
        mock_get_universities.return_value = edx_universities
        mock_get_universities_count.return_value = len(edx_universities)

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{settings.EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        import_universities()

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    def test_import_universities_error(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that universities are not created from the edx universities if the code
        is null.
        """
        edx_university = edx_factories.EdxUniversityFactory(
            code=None,
        )
        mock_get_universities.return_value = [edx_university]
        mock_get_universities_count.return_value = len([edx_university])

        import_universities()

        self.assertEqual(models.Organization.objects.count(), 0)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_update(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that universities are updated from the edx universities and that their
        logos are downloaded.
        """
        organization = factories.OrganizationFactory.create(
            code="orga",
            title="Organization 1 old title",
            logo=None,
        )
        edx_universities = [
            edx_factories.EdxUniversityFactory.create(
                code=organization.code,
                name="Organization 1",
            )
        ]
        mock_get_universities.return_value = edx_universities
        mock_get_universities_count.return_value = len(edx_universities)

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{settings.EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        import_universities()

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    def test_import_universities_create_dry_run(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that no university is created from the edx universities in dry run mode.
        """
        edx_universities = edx_factories.EdxUniversityFactory.create_batch(10)
        mock_get_universities.return_value = edx_universities
        mock_get_universities_count.return_value = len(edx_universities)

        import_universities(dry_run=True)

        self.assertEqual(models.Organization.objects.count(), 0)
