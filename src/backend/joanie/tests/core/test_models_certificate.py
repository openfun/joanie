"""Test suite for Certificate Model"""
from io import BytesIO

from django.conf import settings
from django.test import TestCase

from parler.utils.context import switch_language
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE
from joanie.core.factories import (
    CertificateDefinitionFactory,
    CertificateFactory,
    CourseFactory,
    OrderFactory,
    OrganizationFactory,
    ProductFactory,
)


class CertificateModelTestCase(TestCase):
    """Certificate model test case."""

    def test_models_certificate_localized_context(self):
        """
        When a certificate is created, localized contexts in each enabled languages
        should be created.
        """
        certificate = CertificateFactory()
        languages = settings.LANGUAGES

        self.assertEqual(len(list(certificate.localized_context)), len(languages))

    def test_models_certificate_get_document_context(self):
        """
        We should get the document context in the provided language. If the translation
        does not exist, we should gracefully fallback to the default language defined
        through parler settings ("en-us" in our case).
        """
        organization = OrganizationFactory(title="Organization 1")
        course = CourseFactory(organization=organization)
        product = ProductFactory(
            title="Graded product", courses=[course], type=PRODUCT_TYPE_CERTIFICATE
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Établissement 1")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = OrderFactory(product=product)
        certificate = CertificateFactory(order=order)

        context = certificate.get_document_context("en-us")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["course"]["organization"]["name"], "Organization 1")

        context = certificate.get_document_context("fr-fr")
        self.assertEqual(context["course"]["name"], "Produit certifiant")
        self.assertEqual(context["course"]["organization"]["name"], "Établissement 1")

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = certificate.get_document_context("de-de")
        self.assertEqual(context["course"]["name"], "Graded product")
        self.assertEqual(context["course"]["organization"]["name"], "Organization 1")

    def test_models_certificate_document(self):
        """
        Certificate document property should generate a document
        in the active language.
        """
        organization = OrganizationFactory(
            title="University X", representative="Joanie Cunningham"
        )
        course = CourseFactory(organization=organization)
        certificate_definition = CertificateDefinitionFactory()
        product = ProductFactory(
            title="Graded product",
            courses=[course],
            type=PRODUCT_TYPE_CERTIFICATE,
            certificate_definition=certificate_definition,
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Université X")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = OrderFactory(product=product)
        certificate = CertificateFactory(order=order)

        document_text = pdf_extract_text(BytesIO(certificate.document)).replace(
            "\n", ""
        )
        self.assertRegex(
            document_text, r"Joanie Cunningham.*University X.*Graded product"
        )

        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(BytesIO(certificate.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"Joanie Cunningham.*Université X")

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document_text = pdf_extract_text(BytesIO(certificate.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"Joanie Cunningham.*University X")
