"""Tests for the import_certificates task."""

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter,too-many-locals
import os
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

import responses
from hashids import Hashids

from joanie.core import factories, models
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.utils import image_to_base64
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks.certificates import import_certificates
from joanie.edx_imports.utils import extract_course_number, make_date_aware
from joanie.lms_handler.backends.openedx import OPENEDX_MODE_VERIFIED

SIGNATURE_NAME = "creative_common.jpeg"
with open(
    join(dirname(realpath(__file__)), f"images/{SIGNATURE_NAME}"), "rb"
) as signature_image:
    SIGNATURE_CONTENT = signature_image.read()
    SIGNATURE_CONTENT_BASE64 = image_to_base64(signature_image.name)


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
class EdxImportCertificatesTestCase(TestCase):
    """Tests for the import_certificates task."""

    maxDiff = None

    def setUp(self):
        """Set up the test case."""
        self.hashids = Hashids(salt=settings.EDX_SECRET)
        factories.CertificateDefinitionFactory.create(name=DEGREE)
        factories.CertificateDefinitionFactory.create(name=CERTIFICATE)

    def tearDown(self):
        """Tear down the test case."""
        edx_factories.session.rollback()

    @patch("joanie.edx_imports.edx_mongodb.get_enrollment")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_certificates_create(
        self, mock_get_certificates, mock_get_certificates_count, mock_get_enrollment
    ):
        """
        Test that certificates are created from the edx certificates.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[factories.OrganizationFactory.create()],
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

            edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
            mongo_enrollments[edx_certificate.id] = (
                course.organizations.first().code,
                edx_mongo_signatory,
            )
            responses.add(
                responses.GET,
                f"https://{settings.EDX_DOMAIN}{edx_mongo_signatory.get('signature_image_path')}",
                body=SIGNATURE_CONTENT,
            )

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_enrollment.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        import_certificates()

        self.assertEqual(models.Certificate.objects.count(), len(edx_certificates))
        for edx_certificate in edx_certificates:
            certificate = models.Certificate.objects.get(
                enrollment__user__username=edx_certificate.user.username,
                enrollment__course_run__course__code=extract_course_number(
                    edx_certificate.course_id
                ),
            )
            certificate_name = (
                DEGREE if edx_certificate.mode == OPENEDX_MODE_VERIFIED else CERTIFICATE
            )
            self.assertEqual(certificate.certificate_definition.name, certificate_name)
            self.assertEqual(
                certificate.organization.code,
                mongo_enrollments[edx_certificate.id][0],
            )
            self.assertEqual(
                certificate.issued_on, make_date_aware(edx_certificate.created_date)
            )

            mongo_signatory = mongo_enrollments[edx_certificate.id][1]
            self.assertEqual(
                certificate.localized_context,
                {
                    "signatory": mongo_signatory,
                    "verification_hash": self.hashids.encode(edx_certificate.id),
                    "en-us": {
                        "course": {
                            "name": (
                                certificate.enrollment.course_run.course.safe_translation_getter(
                                    "title", language_code="en"
                                )
                            ),
                        },
                        "organizations": [
                            {
                                "name": certificate.organization.safe_translation_getter(
                                    "title", language_code="en"
                                ),
                                "representative": mongo_signatory.get("name"),
                                "signature": SIGNATURE_CONTENT_BASE64,
                                "logo": image_to_base64(certificate.organization.logo),
                            }
                        ],
                    },
                    "fr-fr": {
                        "course": {
                            "name": (
                                certificate.enrollment.course_run.course.safe_translation_getter(
                                    "title", language_code="fr"
                                )
                            ),
                        },
                        "organizations": [
                            {
                                "name": certificate.organization.safe_translation_getter(
                                    "title", language_code="fr"
                                ),
                                "representative": mongo_signatory.get("name"),
                                "signature": SIGNATURE_CONTENT_BASE64,
                                "logo": image_to_base64(certificate.organization.logo),
                            }
                        ],
                    },
                },
            )
            self.assertTrue(
                default_storage.exists(
                    certificate.localized_context.get("signatory").get(
                        "signature_image_path"
                    )[1:]
                )
            )

    @patch("joanie.edx_imports.edx_mongodb.get_enrollment")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_certificates_update(
        self, mock_get_certificates, mock_get_certificates_count, mock_get_enrollment
    ):
        """
        Test that certificates are updated from the edx certificates.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[factories.OrganizationFactory.create()],
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
            certificate_name = (
                DEGREE if edx_certificate.mode == OPENEDX_MODE_VERIFIED else CERTIFICATE
            )
            factories.EnrollmentCertificateFactory.create(
                certificate_definition__name=certificate_name,
                enrollment=enrollment,
                issued_on=make_date_aware(edx_certificate.created_date),
            )

            edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
            mongo_enrollments[edx_certificate.id] = (
                course.organizations.first().code,
                edx_mongo_signatory,
            )
            responses.add(
                responses.GET,
                f"https://{settings.EDX_DOMAIN}{edx_mongo_signatory.get('signature_image_path')}",
                body=SIGNATURE_CONTENT,
            )

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_enrollment.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        import_certificates()

        self.assertEqual(models.Certificate.objects.count(), len(edx_certificates))
        for edx_certificate in edx_certificates:
            certificate = models.Certificate.objects.get(
                enrollment__user__username=edx_certificate.user.username,
                enrollment__course_run__course__code=extract_course_number(
                    edx_certificate.course_id
                ),
            )
            certificate_name = (
                DEGREE if edx_certificate.mode == OPENEDX_MODE_VERIFIED else CERTIFICATE
            )
            self.assertEqual(certificate.certificate_definition.name, certificate_name)
            self.assertNotEqual(
                certificate.organization.code,
                mongo_enrollments[edx_certificate.id][0],
            )
            self.assertNotEqual(
                certificate.issued_on, make_date_aware(edx_certificate.created_date)
            )

    @patch("joanie.edx_imports.edx_mongodb.get_enrollment")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_certificates_create_missing_joanie_enrollments(
        self, mock_get_certificates, mock_get_certificates_count, mock_get_enrollment
    ):
        """
        Test that certificates are not created from the edx certificates if the enrollment
        is missing in Joanie.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        edx_certificates_with_joanie_enrollments = []
        i = 0
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[factories.OrganizationFactory.create()],
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
            mongo_enrollments[edx_certificate.id] = (
                course.organizations.first().code,
                edx_mongo_signatory,
            )
            i += 1

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_enrollment.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates_with_joanie_enrollments
        ]

        import_certificates()

        self.assertEqual(
            models.Certificate.objects.count(),
            len(edx_certificates_with_joanie_enrollments),
        )
        for edx_certificate in edx_certificates_with_joanie_enrollments:
            self.assertTrue(
                models.Certificate.objects.filter(
                    enrollment__user__username=edx_certificate.user.username,
                    enrollment__course_run__course__code=extract_course_number(
                        edx_certificate.course_id
                    ),
                ).exists()
            )

    @patch("joanie.edx_imports.edx_mongodb.get_enrollment")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_certificates_create_missing_mongodb_orga(
        self, mock_get_certificates, mock_get_certificates_count, mock_get_enrollment
    ):
        """
        Test that certificates are not created from the edx certificates if the organization
        is missing in mongodb.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        edx_certificates_with_mongodb_enrollments = []
        i = 0
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[factories.OrganizationFactory.create()],
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

            edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
            if i % 2 == 0:
                edx_certificates_with_mongodb_enrollments.append(edx_certificate)
                mongo_enrollments[edx_certificate.id] = (
                    course.organizations.first().code,
                    edx_mongo_signatory,
                )
                responses.add(
                    responses.GET,
                    f"https://{settings.EDX_DOMAIN}"
                    f"{edx_mongo_signatory.get('signature_image_path')}",
                    body=SIGNATURE_CONTENT,
                )
            else:
                mongo_enrollments[edx_certificate.id] = (
                    None,
                    edx_mongo_signatory,
                )
            i += 1

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_enrollment.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        import_certificates()

        self.assertEqual(
            models.Certificate.objects.count(),
            len(edx_certificates_with_mongodb_enrollments),
        )
        for edx_certificate in edx_certificates_with_mongodb_enrollments:
            self.assertTrue(
                models.Certificate.objects.filter(
                    enrollment__user__username=edx_certificate.user.username,
                    enrollment__course_run__course__code=extract_course_number(
                        edx_certificate.course_id
                    ),
                ).exists()
            )

    @patch("joanie.edx_imports.edx_mongodb.get_enrollment")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_certificates")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_certificates_create_missing_mongodb_signatory(
        self, mock_get_certificates, mock_get_certificates_count, mock_get_enrollment
    ):
        """
        Test that certificates are created from the edx certificates with missing signatory.
        """
        edx_certificates = edx_factories.EdxGeneratedCertificateFactory.create_batch(10)
        mongo_enrollments = {}
        edx_certificates_with_mongodb_enrollments = []
        i = 0
        for edx_certificate in edx_certificates:
            course = factories.CourseFactory.create(
                code=extract_course_number(edx_certificate.course_id),
                organizations=[factories.OrganizationFactory.create()],
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
            if i % 2 == 0:
                edx_certificates_with_mongodb_enrollments.append(edx_certificate)

                edx_mongo_signatory = edx_factories.EdxMongoSignatoryFactory()
                mongo_enrollments[edx_certificate.id] = (
                    course.organizations.first().code,
                    edx_mongo_signatory,
                )
                responses.add(
                    responses.GET,
                    f"https://{settings.EDX_DOMAIN}"
                    f"{edx_mongo_signatory.get('signature_image_path')}",
                    body=SIGNATURE_CONTENT,
                )
            else:
                mongo_enrollments[edx_certificate.id] = (
                    course.organizations.first().code,
                    None,
                )
            i += 1

        mock_get_certificates.return_value = edx_certificates
        mock_get_certificates_count.return_value = len(edx_certificates)
        mock_get_enrollment.side_effect = [
            mongo_enrollments[edx_certificate.id]
            for edx_certificate in edx_certificates
        ]

        import_certificates()

        self.assertEqual(
            models.Certificate.objects.count(),
            len(edx_certificates),
        )
        for edx_certificate in edx_certificates:
            certificate = models.Certificate.objects.get(
                enrollment__user__username=edx_certificate.user.username,
                enrollment__course_run__course__code=extract_course_number(
                    edx_certificate.course_id
                ),
            )
            certificate_name = (
                DEGREE if edx_certificate.mode == OPENEDX_MODE_VERIFIED else CERTIFICATE
            )
            self.assertEqual(certificate.certificate_definition.name, certificate_name)
            self.assertEqual(
                certificate.organization.code,
                mongo_enrollments[edx_certificate.id][0],
            )
            self.assertEqual(
                certificate.issued_on, make_date_aware(edx_certificate.created_date)
            )
            if edx_certificate in edx_certificates_with_mongodb_enrollments:
                signature = SIGNATURE_CONTENT_BASE64
            else:
                signature = None

            mongo_signatory = mongo_enrollments[edx_certificate.id][1]
            mongo_signatory_name = (
                mongo_signatory.get("name") if mongo_signatory else None
            )
            self.assertEqual(
                certificate.localized_context,
                {
                    "signatory": mongo_signatory,
                    "verification_hash": self.hashids.encode(edx_certificate.id),
                    "en-us": {
                        "course": {
                            "name": (
                                certificate.enrollment.course_run.course.safe_translation_getter(
                                    "title", language_code="en"
                                )
                            ),
                        },
                        "organizations": [
                            {
                                "name": certificate.organization.safe_translation_getter(
                                    "title", language_code="en"
                                ),
                                "representative": mongo_signatory_name,
                                "signature": signature,
                                "logo": image_to_base64(certificate.organization.logo),
                            }
                        ],
                    },
                    "fr-fr": {
                        "course": {
                            "name": (
                                certificate.enrollment.course_run.course.safe_translation_getter(
                                    "title", language_code="fr"
                                )
                            ),
                        },
                        "organizations": [
                            {
                                "name": certificate.organization.safe_translation_getter(
                                    "title", language_code="fr"
                                ),
                                "representative": mongo_signatory_name,
                                "signature": signature,
                                "logo": image_to_base64(certificate.organization.logo),
                            }
                        ],
                    },
                },
            )
