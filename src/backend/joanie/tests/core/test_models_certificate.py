"""Test suite for Certificate Model"""
from django.conf import settings
from django.test import TestCase

from joanie.core import factories


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
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[],
            title="Graded product",
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Établissement 1")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = factories.OrderFactory(product=product, organization=organization)
        certificate = factories.OrderCertificateFactory(order=order)

        context = certificate.get_document_context("en-us")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["organization"]["name"], "Organization 1")

        context = certificate.get_document_context("fr-fr")
        self.assertEqual(context["course"]["name"], "Produit certifiant")
        self.assertEqual(context["organization"]["name"], "Établissement 1")

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = certificate.get_document_context("de-de")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["organization"]["name"], "Organization 1")

    def test_models_certificate_get_document_context_with_incomplete_information_raises_error(
        self,
    ):
        """
        If the certificate context is incomplete (missing logo or signature for example),
        it should raise a Value Error while getting the document's context.
        """
        organization = factories.OrganizationFactory(
            title="University X",
            representative="Joanie Cunningham",
            logo=None,
            signature=None,
        )

        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[],
            title="Graded product",
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        order = factories.OrderFactory(product=product, organization=organization)
        certificate = factories.OrderCertificateFactory(order=order)

        # - Retrieve the document context should raise a ValueError
        with self.assertRaises(ValueError) as context:
            certificate.get_document_context()

        self.assertEqual(
            str(context.exception),
            "The 'signature' attribute has no file associated with it.",
        )
