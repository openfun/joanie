# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""Test case for the populate_signatory_certificates task"""

import os
import uuid
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

import responses

from joanie.core import factories
from joanie.core.utils import file_checksum
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks import populate_signatory_certificates_task
from joanie.tests.base import BaseLogMixinTestCase

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
class PopulateSignatoryCertificatesTestCase(TestCase, BaseLogMixinTestCase):
    """Test case for the populate_signatory_certificates task"""

    def test_populate_signatory_certificates_task_empty_queryset(self):
        """If there is no certificate to process, an empty report should be returned."""

        report = populate_signatory_certificates_task(certificate_id=uuid.uuid4())

        self.assertEqual(
            report, "0 certificates processed, 0 populated, 0 skipped, 0 errors"
        )

    @patch("joanie.core.models.Enrollment.set")
    def test_populate_signatory_certificates_task_unknown_resource_link(self, _):
        """
        If no course_id is passed and the related course run resource_link can't be
        parsed, an error should be reported
        """
        factories.EnrollmentCertificateFactory(
            certificate_definition__template="degree",
            enrollment__course_run__resource_link="https://openedx.com/unknown",
        )
        report = populate_signatory_certificates_task()

        self.assertEqual(
            report, "1 certificates processed, 0 populated, 0 skipped, 1 errors"
        )

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_populate_signatory_certificates_task_manage_exception(
        self, _, mock_get_signatory_from_course_id
    ):
        """
        If an exception is raised during a certificate processing, it should be reported
        and the process should not be stopped.
        """
        organization = factories.OrganizationFactory(signature=None)
        factories.EnrollmentCertificateFactory.create_batch(
            3,
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )

        edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
        mock_get_signatory_from_course_id.side_effect = [
            Exception("Error during MongoDB signatory retrieval"),
            edx_mongo_signatory,
            edx_mongo_signatory,
        ]
        responses.add(
            responses.GET,
            f"https://{settings.EDX_DOMAIN}"
            f"{edx_mongo_signatory.get('signature_image_path')}",
            body=SIGNATURE_CONTENT,
        )

        with self.assertLogs() as logger:
            report = populate_signatory_certificates_task()

        self.assertEqual(
            report, "3 certificates processed, 2 populated, 0 skipped, 1 errors"
        )
        self.assertLogsContains(logger, ["Error during MongoDB signatory retrieval"])

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_populate_signatory_certificates_task_retrieve_signatory_from_edx(
        self, _, mock_get_signatory_from_course_id
    ):
        """The task should try to retrieve signatory from edx first."""
        organization = factories.OrganizationFactory(signature=None)
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

        report = populate_signatory_certificates_task()
        self.assertEqual(
            report, "1 certificates processed, 1 populated, 0 skipped, 0 errors"
        )

        cert.refresh_from_db()
        organization_context = cert.localized_context["en-us"]["organizations"][0]
        signature = cert.images.get(checksum=SIGNATURE_CHECKSUM)
        self.assertEqual(
            organization_context["representative"], edx_mongo_signatory["name"]
        )
        self.assertEqual(
            organization_context["representative_profession"],
            edx_mongo_signatory["title"],
        )
        self.assertEqual(organization_context["signature_id"], str(signature.id))

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_populate_signatory_certificates_task_retrieve_signatory_from_organization(
        self, _, mock_get_signatory_from_course_id
    ):
        """If OpenEdX returns no signatory, we should fallback to the certificate organization."""
        organization = factories.OrganizationFactory()
        cert = factories.EnrollmentCertificateFactory(
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )
        # Update cert localized context to remove signatory information
        for language, _ in settings.LANGUAGES:
            cert.localized_context[language]["organizations"][0]["representative"] = ""
            cert.localized_context[language]["organizations"][0][
                "representative_profession"
            ] = ""
            del cert.localized_context[language]["organizations"][0]["signature_id"]
        cert.save()

        mock_get_signatory_from_course_id.return_value = None

        report = populate_signatory_certificates_task()
        self.assertEqual(
            report, "1 certificates processed, 1 populated, 0 skipped, 0 errors"
        )

        cert.refresh_from_db()
        organization_context = cert.localized_context["en-us"]["organizations"][0]
        signature = cert.images.get(checksum=file_checksum(organization.signature))
        self.assertEqual(
            organization_context["representative"], organization.representative
        )
        self.assertEqual(
            organization_context["representative_profession"],
            organization.representative_profession,
        )
        self.assertEqual(organization_context["signature_id"], str(signature.id))

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_populate_signatory_certificates_task_retrieve_signatory_from_organization_signatory(
        self, _, mock_get_signatory_from_course_id
    ):
        """If an Organization has signatory name, it should be used over the representative."""
        organization = factories.OrganizationFactory(
            signatory_representative="John Doe",
            signatory_representative_profession="Official signatory",
        )
        cert = factories.EnrollmentCertificateFactory(
            certificate_definition__template="degree",
            organization=organization,
            enrollment__course_run__course__organizations=[organization],
        )
        # Update cert localized context to remove signatory information
        for language, _ in settings.LANGUAGES:
            cert.localized_context[language]["organizations"][0]["representative"] = ""
            cert.localized_context[language]["organizations"][0][
                "representative_profession"
            ] = ""
            del cert.localized_context[language]["organizations"][0]["signature_id"]
        cert.save()

        mock_get_signatory_from_course_id.return_value = None

        report = populate_signatory_certificates_task()
        self.assertEqual(
            report, "1 certificates processed, 1 populated, 0 skipped, 0 errors"
        )

        cert.refresh_from_db()
        organization_context = cert.localized_context["en-us"]["organizations"][0]
        signature = cert.images.get(checksum=file_checksum(organization.signature))
        self.assertEqual(
            organization_context["representative"],
            organization.signatory_representative,
        )
        self.assertEqual(
            organization_context["representative_profession"],
            organization.signatory_representative_profession,
        )
        self.assertEqual(organization_context["signature_id"], str(signature.id))
