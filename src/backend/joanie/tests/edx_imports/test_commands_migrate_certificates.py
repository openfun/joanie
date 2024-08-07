"""Tests for the migrate_edx command to import certificates from Open edX."""

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter,too-many-locals

import os
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

import responses

from joanie.core import factories, models
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.utils import image_to_base64
from joanie.edx_imports import edx_factories
from joanie.edx_imports.utils import (
    extract_course_number,
    extract_organization_code,
    make_date_aware,
)
from joanie.lms_handler.backends.openedx import OPENEDX_MODE_VERIFIED
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)

SIGNATURE_NAME = "creative_common.jpeg"
with open(
    join(dirname(realpath(__file__)), f"images/{SIGNATURE_NAME}"), "rb"
) as signature_image:
    SIGNATURE_CONTENT = signature_image.read()
    SIGNATURE_CONTENT_BASE64 = image_to_base64(signature_image.name)


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
class MigrateOpenEdxCertificatesTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the migrate_edx command to import certificates from Open edX."""

    def setUp(self):
        super().setUp()
        factories.CertificateDefinitionFactory.create(template=DEGREE)
        factories.CertificateDefinitionFactory.create(template=CERTIFICATE)

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_command_migrate_certificates_create(
        self,
        _,
        mock_get_certificates,
        mock_get_certificates_count,
        mock_get_signatory_from_course_id,
    ):
        """
        Test that certificates are created from the edx certificates.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[
                    factories.OrganizationFactory.create(
                        code=extract_organization_code(edx_certificate.course_id)
                    )
                ],
            )
            course_run = factories.CourseRunFactory.create(
                course=course,
                state=models.CourseState.ONGOING_OPEN,
                resource_link=f"http://openedx.test/courses/{edx_certificate.course_id}/course/",
                is_listed=True,
            )
            factories.EnrollmentFactory.create(
                user__username=edx_certificate.user.username,
                course_run=course_run,
                was_created_by_order=False,
            )

            if edx_certificate.mode == OPENEDX_MODE_VERIFIED:
                edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
                mongo_enrollments[edx_certificate.id] = edx_mongo_signatory
                responses.add(
                    responses.GET,
                    f"https://{settings.EDX_DOMAIN}"
                    + edx_mongo_signatory.get("signature_image_path"),
                    body=SIGNATURE_CONTENT,
                )
            else:
                mongo_enrollments[edx_certificate.id] = None

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_signatory_from_course_id.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--certificates")

        expected = [
            "Importing data from Open edX database...",
            "Importing certificates...",
            "10 certificates to import by batch of 1000",
            "100% 10/10 : 10 certificates created, 0 skipped, 0 errors",
            "1 import certificates tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @patch("joanie.core.models.Enrollment.set")
    def test_command_migrate_certificates_update(
        self,
        _,
        mock_get_certificates,
        mock_get_certificates_count,
        mock_get_signatory_from_course_id,
    ):
        """
        Test that certificates are updated from the edx certificates.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[
                    factories.OrganizationFactory.create(
                        code=extract_organization_code(edx_certificate.course_id)
                    )
                ],
            )
            course_run = factories.CourseRunFactory.create(
                course=course,
                state=models.CourseState.ONGOING_OPEN,
                resource_link=f"http://openedx.test/courses/{edx_certificate.course_id}/course/",
                is_listed=True,
            )
            enrollment = factories.EnrollmentFactory.create(
                user__username=edx_certificate.user.username,
                course_run=course_run,
                was_created_by_order=False,
            )
            factories.EnrollmentCertificateFactory.create(
                certificate_definition__name="degree",
                enrollment=enrollment,
                issued_on=make_date_aware(edx_certificate.created_date),
            )

            edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
            mongo_enrollments[edx_certificate.id] = edx_mongo_signatory

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_signatory_from_course_id.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--certificates")

        expected = [
            "Importing data from Open edX database...",
            "Importing certificates...",
            "10 certificates to import by batch of 1000",
            "100% 10/10 : 0 certificates created, 10 skipped, 0 errors",
            "1 import certificates tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_command_migrate_certificates_create_missing_joanie_enrollments(
        self,
        _,
        mock_get_certificates,
        mock_get_certificates_count,
        mock_get_signatory_from_course_id,
    ):
        """
        Test that certificates are not created from the edx certificates if the enrollment
        is missing in Joanie.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(
            10, mode=OPENEDX_MODE_VERIFIED
        )
        mongo_enrollments = {}
        edx_certificates_with_joanie_enrollments = []
        edx_certificates_fail = []
        i = 0
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[
                    factories.OrganizationFactory.create(
                        code=extract_organization_code(edx_certificate.course_id)
                    )
                ],
            )

            edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
            if i % 2 == 0:
                course_run = factories.CourseRunFactory.create(
                    course=course,
                    state=models.CourseState.ONGOING_OPEN,
                    resource_link=(
                        "http://openedx.test/courses/"
                        f"{edx_certificate.course_id}/course/"
                    ),
                    is_listed=True,
                )
                factories.EnrollmentFactory.create(
                    user__username=edx_certificate.user.username,
                    course_run=course_run,
                    was_created_by_order=False,
                )
                edx_certificates_with_joanie_enrollments.append(edx_certificate)
                responses.add(
                    responses.GET,
                    f"https://{settings.EDX_DOMAIN}"
                    f"{edx_mongo_signatory.get('signature_image_path')}",
                    body=SIGNATURE_CONTENT,
                )
            else:
                edx_certificates_fail.append(edx_certificate)
            mongo_enrollments[edx_certificate.id] = edx_mongo_signatory
            i += 1

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_signatory_from_course_id.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates_with_joanie_enrollments
        ]

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--certificates")

        expected = [
            "Importing data from Open edX database...",
            "Importing certificates...",
            "10 certificates to import by batch of 1000",
            "100% 10/10 : 5 certificates created, 0 skipped, 5 errors",
            "1 import certificates tasks launched",
        ] + [
            f"No Enrollment found for {edx_certificate.user.username} {edx_certificate.course_id}"
            for edx_certificate in edx_certificates_fail
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_mongodb.get_signatory_from_course_id")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @patch("joanie.core.models.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=False)
    def test_command_migrate_certificates_create_dry_run_offset_size(
        self,
        _,
        mock_get_certificates,
        mock_get_certificates_count,
        mock_get_signatory_from_course_id,
    ):
        """
        Test that certificates are created from the edx certificates.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(
            100
        )
        mongo_enrollments = {}
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[
                    factories.OrganizationFactory.create(
                        code=extract_organization_code(edx_certificate.course_id)
                    )
                ],
            )
            course_run = factories.CourseRunFactory.create(
                course=course,
                state=models.CourseState.ONGOING_OPEN,
                resource_link=f"http://openedx.test/courses/{edx_certificate.course_id}/course/",
                is_listed=True,
            )
            factories.EnrollmentFactory.create(
                user__username=edx_certificate.user.username,
                course_run=course_run,
                was_created_by_order=False,
            )

            if edx_certificate.mode == OPENEDX_MODE_VERIFIED:
                edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
                mongo_enrollments[edx_certificate.id] = edx_mongo_signatory
                responses.add(
                    responses.GET,
                    f"https://{settings.EDX_DOMAIN}"
                    + edx_mongo_signatory.get("signature_image_path"),
                    body=SIGNATURE_CONTENT,
                )
            else:
                mongo_enrollments[edx_certificate.id] = None

        def get_edx_certificates(*args, **kwargs):
            start = args[0]
            stop = start + args[1]
            return edx_certificates[start:stop]

        mock_get_certificates.side_effect = get_edx_certificates
        mock_get_certificates_count.return_value = 10

        mock_get_signatory_from_course_id.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        with self.assertLogs() as logger:
            call_command(
                "migrate_edx",
                "--skip-check",
                "--certificates",
                "--certificates-offset=20",
                "--certificates-size=10",
                "--dry-run",
            )

        expected = [
            "Importing data from Open edX database...",
            "Importing certificates...",
            "10 certificates to import by batch of 1000",
            "100% 100/10 : 80 certificates created, 0 skipped, 0 errors",
            "1 import certificates tasks launched",
        ]
        self.assertLogsContains(logger, expected)
