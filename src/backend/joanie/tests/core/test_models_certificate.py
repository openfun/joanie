"""Test suite for Certificate Model"""

from django.conf import settings
from django.test import override_settings

from joanie.core import enums, factories
from joanie.core.models import Certificate, DocumentImage
from joanie.tests.base import LoggingTestCase


@override_settings(LANGUAGE_CODE="en-us")
class CertificateModelTestCase(LoggingTestCase):
    """Certificate model test case."""

    maxDiff = None

    def test_models_certificate_localized_context(self):
        """
        When a certificate is created, localized contexts in each enabled languages
        should be created and related images set.
        """
        certificate = factories.OrderCertificateFactory()
        languages = settings.LANGUAGES

        self.assertEqual(len(list(certificate.localized_context)), len(languages))

    def test_models_certificate_set_localized_context_on_create(self):
        """
        When a certificate is created, localized contexts in each enabled languages
        is created. DocumentImage relations should be also created.
        """
        organization = factories.OrganizationFactory(
            title="University 1",
            representative="Joanie Cunningham",
            representative_profession="Teacher",
        )
        organization.translations.create(title="Université 1")
        course = factories.CourseFactory(title="Course 1", organizations=[organization])
        course.translations.create(title="Cours 1")
        enrollment = factories.EnrollmentFactory(course_run__course=course)
        definition = factories.CertificateDefinitionFactory()

        # No DocumentImage should exist yet
        self.assertEqual(DocumentImage.objects.count(), 0)

        certificate = Certificate.objects.create(
            certificate_definition=definition,
            organization=organization,
            enrollment=enrollment,
        )

        # After creation, a DocumentImage should have been created
        # logo and signature images are the same when using OrganizationFactory
        self.assertEqual(DocumentImage.objects.count(), 1)
        # relation to the DocumentImage should have been set
        self.assertEqual(certificate.images.count(), 1)

        image_id = str(DocumentImage.objects.first().id)
        languages = settings.LANGUAGES
        self.assertEqual(
            certificate.localized_context,
            {
                language_code: {
                    "course": {
                        "name": course.safe_translation_getter("title", language_code)
                    },
                    "organizations": [
                        {
                            "name": organization.safe_translation_getter(
                                "title", language_code
                            ),
                            "representative": organization.representative,
                            "representative_profession": organization.representative_profession,
                            "signature_id": image_id,
                            "logo_id": image_id,
                        }
                    ],
                    "certification_level": None,
                    "skills": [],
                    "teachers": [],
                }
                for (language_code, _) in languages
            },
        )

    def test_models_certificate_set_localized_context_dont_duplicate_images(self):
        """On localized context creation, DocumentImage should not be duplicated."""
        organization = factories.OrganizationFactory()
        enrollment = factories.EnrollmentFactory(
            course_run__course__organizations=[organization]
        )

        # Create a DocumentImage for the organization
        image = DocumentImage.objects.create(file=organization.logo)

        cert = factories.EnrollmentCertificateFactory(enrollment=enrollment)
        cert.refresh_from_db()

        # No new DocumentImage should have been created
        self.assertEqual(DocumentImage.objects.count(), 1)

        # A relation to the existing image should have been set
        self.assertEqual(cert.images.count(), 1)
        self.assertEqual(cert.images.first(), image)

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_models_certificate_get_document_context(self):
        """
        We should get the document context in the provided language. If the translation
        does not exist, we should gracefully fallback to the default language defined
        through parler settings ("en-us" in our case).
        """
        organization = factories.OrganizationFactory(title="Organization 1")
        course = factories.CourseFactory(organizations=[organization])
        product = factories.ProductFactory(
            courses=[],
            title="Graded product",
        )
        factories.OfferingFactory(course=course, product=product)

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Établissement 1")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = factories.OrderFactory(product=product)
        certificate = factories.OrderCertificateFactory(order=order)

        context = certificate.get_document_context("en-us")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(len(context["organizations"]), 1)
        self.assertEqual(context["organizations"][0]["name"], "Organization 1")
        self.assertEqual(context["site"]["name"], "Test Catalog")
        self.assertEqual(context["site"]["hostname"], "https://richie.education")

        context = certificate.get_document_context("fr-fr")
        self.assertEqual(context["course"]["name"], "Produit certifiant")
        self.assertEqual(context["organizations"][0]["name"], "Établissement 1")
        self.assertEqual(context["site"]["name"], "Test Catalog")
        self.assertEqual(context["site"]["hostname"], "https://richie.education")

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = certificate.get_document_context("de-de")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["organizations"][0]["name"], "Organization 1")
        self.assertEqual(context["site"]["name"], "Test Catalog")
        self.assertEqual(context["site"]["hostname"], "https://richie.education")

    def test_models_certificate_get_document_context_with_incomplete_information(
        self,
    ):
        """
        If logo or signature are missing from the organization, the context should be
        returned with None values for these fields.
        """
        organization = factories.OrganizationFactory(
            title="University X",
            representative="Joanie Cunningham",
            logo=None,
            signature=None,
        )

        course = factories.CourseFactory(organizations=[organization])
        product = factories.ProductFactory(
            courses=[course],
            title="Graded product",
        )

        order = factories.OrderFactory(product=product, organization=organization)

        # - Retrieve the document context should raise a ValueError

        certificate = factories.OrderCertificateFactory(order=order)

        context = certificate.get_document_context("en-us")
        self.assertIsNone(context["organizations"][0]["logo"])
        self.assertIsNone(context["organizations"][0]["signature"])

    def test_models_certificate_verification_uri(self):
        """
        The verification uri should be returned only for degree certificates.
        """
        for [template_name, _] in enums.CERTIFICATE_NAME_CHOICES:
            certificate = factories.EnrollmentCertificateFactory(
                certificate_definition__template=template_name
            )
            if template_name in enums.VERIFIABLE_CERTIFICATES:
                self.assertEqual(
                    certificate.verification_uri,
                    f"https://example.com/en-us/certificates/{certificate.id}",
                )
            else:
                self.assertIsNone(certificate.verification_uri)

    def test_models_certificate_get_document_context_missing_logo_raise_logger_error(
        self,
    ):
        """
        When getting the document context for a certificate, of type certificate or degree,
        if the organization does not have a logo stored, it should trigger a logger error
        with the 'id' of the organization concerned
        """
        organization = factories.OrganizationFactory(logo=None)
        course = factories.CourseFactory(organizations=[organization])
        product = factories.ProductFactory(courses=[course])
        certificate = factories.OrderCertificateFactory(
            order__product=product,
            order__organization=organization,
            certificate_definition__template="DEGREE",
        )

        with self.assertLogs() as logger:
            certificate.get_document_context("en-us")

        self.assertLogsContains(
            logger, f"Organization {organization.id} does not have a logo."
        )

        certificate = factories.OrderCertificateFactory(
            order__product=product,
            order__organization=organization,
            certificate_definition__template="CERTIFICATE",
        )

        with self.assertLogs() as logger:
            certificate.get_document_context("en-us")

        self.assertLogsContains(
            logger, f"Organization {organization.id} does not have a logo."
        )
