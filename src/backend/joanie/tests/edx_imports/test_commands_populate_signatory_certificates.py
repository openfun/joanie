# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""Tests the populate_signatory_certificates command."""

import os
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import override_settings

import responses

from joanie.core import factories
from joanie.core.utils import file_checksum
from joanie.edx_imports import edx_factories
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)

SIGNATURE_NAME = "creative_common.jpeg"
SIGNATURE_PATH = join(dirname(realpath(__file__)), f"images/{SIGNATURE_NAME}")

with open(SIGNATURE_PATH, "rb") as signature_image:
    SIGNATURE_CONTENT = signature_image.read()
    SIGNATURE_CHECKSUM = file_checksum(ContentFile(content=SIGNATURE_CONTENT))


@override_settings(
    EDX_DOMAIN="openedx.test",
    EDX_SECRET="test",
    EDX_TIME_ZONE="UTC",
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
class PopulateSignatoryCertificatesCommandTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the populate_signatory_certificates command."""

    @patch("joanie.core.models.Enrollment.set")
    def test_command_populate_certificate_signatory_skipped(self, _):
        """
        The command should skip certificates if those one have already a signatory.
        """
        organization = factories.OrganizationFactory()
        certs = factories.EnrollmentCertificateFactory.create_batch(
            3,
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )

        with self.assertLogs() as logger:
            call_command("populate_certificate_signatory", "--skip-check")

        expected = "3 certificates processed, 0 populated, 3 skipped, 0 errors"

        self.assertLogsContains(logger, [expected])
        self.assertIsNotNone(
            certs[0].localized_context["en-us"]["organizations"][0]["representative"]
        )
        self.assertIsNotNone(
            certs[0].localized_context["en-us"]["organizations"][0]["signature_id"]
        )

    @patch("joanie.core.models.Enrollment.set")
    def test_command_populate_certificate_signatory_filter_by_certificate_id(self, _):
        """The command should allow to filter certificates by id."""
        organization = factories.OrganizationFactory()
        [cert, *_] = factories.EnrollmentCertificateFactory.create_batch(
            3,
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )

        with self.assertLogs() as logger:
            call_command(
                "populate_certificate_signatory", "--skip-check", f"--id={cert.id}"
            )

        expected = "1 certificates processed, 0 populated, 1 skipped, 0 errors"

        self.assertLogsContains(logger, [expected])
        self.assertIsNotNone(
            cert.localized_context["en-us"]["organizations"][0]["representative"]
        )
        self.assertIsNotNone(
            cert.localized_context["en-us"]["organizations"][0]["signature_id"]
        )

    @patch("joanie.core.models.Enrollment.set")
    def test_command_populate_certificate_signatory_filter_by_course_id(self, _):
        """The command should allow to filter certificates by course id."""
        organization = factories.OrganizationFactory()
        course_id = "course-v1:fun+101+run01"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        factories.EnrollmentCertificateFactory.create_batch(
            3,
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
            enrollment__course_run__resource_link=resource_link,
        )
        factories.EnrollmentCertificateFactory.create_batch(
            3,
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )

        with self.assertLogs() as logger:
            call_command(
                "populate_certificate_signatory",
                "--skip-check",
                f"--course-id={course_id}",
            )

        expected = "3 certificates processed, 0 populated, 3 skipped, 0 errors"

        self.assertLogsContains(logger, [expected])

    @patch("joanie.core.models.Enrollment.set")
    def test_command_populate_certificate_signatory_error(self, _):
        """
        The command should report an error if certificate has no organizations in its context.
        """
        cert = factories.EnrollmentCertificateFactory(
            certificate_definition__template="degree",
            enrollment__course_run__course__organizations=[],
        )

        with self.assertLogs() as logger:
            call_command("populate_certificate_signatory", "--skip-check")

        expected = "1 certificates processed, 0 populated, 0 skipped, 1 errors"

        self.assertLogsContains(logger, [expected])
        self.assertEqual(cert.localized_context["en-us"]["organizations"], [])

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_command_populate_certificate_signatory_populate(
        self, _, mock_get_signatory_from_course_id
    ):
        """
        The command should populate the certificate with the signatory information if
        some information are missing.
        """
        organization = factories.OrganizationFactory(representative="")
        cert = factories.EnrollmentCertificateFactory(
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )

        edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
        mock_get_signatory_from_course_id.return_value = edx_mongo_signatory
        responses.add(
            responses.GET,
            f"https://{settings.EDX_DOMAIN}"
            f"{edx_mongo_signatory.get('signature_image_path')}",
            body=SIGNATURE_CONTENT,
        )

        with self.assertLogs() as logger:
            call_command("populate_certificate_signatory", "--skip-check")

        expected = "1 certificates processed, 1 populated, 0 skipped, 0 errors"

        self.assertLogsContains(logger, [expected])
        cert.refresh_from_db()
        self.assertEqual(
            cert.localized_context["en-us"]["organizations"][0]["representative"],
            edx_mongo_signatory["name"],
        )
        self.assertEqual(
            cert.localized_context["en-us"]["organizations"][0][
                "representative_profession"
            ],
            edx_mongo_signatory["title"],
        )
        signature = cert.images.get(checksum=SIGNATURE_CHECKSUM)
        self.assertEqual(
            cert.localized_context["en-us"]["organizations"][0]["signature_id"],
            str(signature.id),
        )
