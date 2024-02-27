"""Tests for the migrate_edx command to import universities from Open edX."""

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

import responses

from joanie.core import factories
from joanie.edx_imports import edx_factories
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)

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
)
class MigrateOpenEdxTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the migrate_edx command to import universities from Open edX."""

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_command_migrate_universities_create(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--universities")

        expected = [
            "Importing data from Open edX database...",
            "Importing universities...",
            "10 universities to import by batch of 1000",
            "Starting Celery task, importing universities...",
            "10 universities created, 0 errors",
            "Done executing Celery importing universities task...",
            "1 import universities tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    def test_command_migrate_universities_update(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--universities")

        expected = [
            "Importing data from Open edX database...",
            "Importing universities...",
            "1 universities to import by batch of 1000",
            "Starting Celery task, importing universities...",
            "0 universities created, 0 errors",
            "Done executing Celery importing universities task...",
            "1 import universities tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_command_migrate_universities_error(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that universities are not created from the edx universities if the code is
        missing.
        """
        edx_university = edx_factories.EdxUniversityFactory(
            code=None,
        )
        mock_get_universities.return_value = [edx_university]
        mock_get_universities_count.return_value = len([edx_university])

        responses.add(
            responses.GET,
            f"https://{settings.EDX_DOMAIN}/media/{edx_university.logo}",
            body=LOGO_CONTENT,
        )

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--universities")

        expected = [
            "Importing data from Open edX database...",
            "Importing universities...",
            "1 universities to import by batch of 1000",
            "Starting Celery task, importing universities...",
            f"Unable to import university {edx_university.code}",
            "{'code': ['This field cannot be null.']}",
            "0 universities created, 1 errors",
            "Done executing Celery importing universities task...",
            "1 import universities tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_universities")
    def test_command_migrate_universities_create_dry_run(
        self, mock_get_universities, mock_get_universities_count
    ):
        """
        Test that universities are not created from the edx universities if the dry-run
        option is set.
        """
        edx_universities = edx_factories.EdxUniversityFactory.create_batch(10)
        mock_get_universities.return_value = edx_universities
        mock_get_universities_count.return_value = len(edx_universities)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--universities", "--dry-run")

        expected = [
            "Importing data from Open edX database...",
            "Importing universities...",
            "Dry run: no university will be imported",
            "10 universities to import by batch of 1000",
            "Starting Celery task, importing universities...",
            "Dry run: 10 universities would be created, 0 errors",
            "Done executing Celery importing universities task...",
            "1 import universities tasks launched",
        ]
        self.assertLogsContains(logger, expected)
