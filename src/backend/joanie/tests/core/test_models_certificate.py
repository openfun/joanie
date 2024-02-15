"""Test suite for Certificate Model"""
from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class CertificateModelTestCase(TestCase):
    """Certificate model test case."""

    def test_models_certificate_localized_context(self):
        """
        When a certificate is created, localized contexts in each enabled languages
        should be created.
        """
        certificate = factories.OrderCertificateFactory()
        languages = settings.LANGUAGES

        self.assertEqual(len(list(certificate.localized_context)), len(languages))

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
        factories.CourseProductRelationFactory(course=course, product=product)

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Établissement 1")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = factories.OrderFactory(product=product)
        certificate = factories.OrderCertificateFactory(order=order)

        context = certificate.get_document_context("en-us")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(len(context["organizations"]), 1)
        self.assertEqual(context["organizations"][0]["name"], "Organization 1")

        context = certificate.get_document_context("fr-fr")
        self.assertEqual(context["course"]["name"], "Produit certifiant")
        self.assertEqual(context["organizations"][0]["name"], "Établissement 1")

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = certificate.get_document_context("de-de")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["organizations"][0]["name"], "Organization 1")

    def test_models_certificate_get_document_context_with_incomplete_information_raises_error(
        self,
    ):
        """
        If the certificate context is incomplete (missing logo or signature for example),
        it should raise a Value Error while creating the certificate.
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
        with self.assertRaises(ValueError) as context:
            factories.OrderCertificateFactory(order=order)

        self.assertEqual(
            str(context.exception),
            "The 'signature' attribute has no file associated with it.",
        )

    def test_models_certificate_verification_uri(self):
        """
        The verification uri should be returned only for degree certificates.
        """
        for [template_name, _] in enums.CERTIFICATE_NAME_CHOICES:
            certificate = factories.EnrollmentCertificateFactory(
                certificate_definition__template=template_name
            )
            if template_name == enums.DEGREE:
                self.assertEqual(
                    certificate.verification_uri,
                    f"https://example.com/en-us/certificates/{certificate.id}",
                )
            else:
                self.assertIsNone(certificate.verification_uri)
