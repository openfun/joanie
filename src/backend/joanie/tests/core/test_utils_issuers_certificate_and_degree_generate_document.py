"""Test suite for utility method to generate document of Certificate/Degree in PDF bytes format."""
from io import BytesIO

from django.test import TestCase

from parler.utils.context import switch_language
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import issuers


class UtilsIssuersCertificateAndDegreeGenerateDocumentTestCase(TestCase):
    """
    Test suite for utility method to generate document of Certificate/Degree in PDF bytes format.
    """

    def test_utils_issuers_generate_document_certificate_degree_document(self):
        """
        The generated document in PDF bytes format should be rendered into the active language
        of the certificate's context. The method `get_document_context` will prepare the data
        in the appropriate language.
        """
        organization = factories.OrganizationFactory(
            title="University X", representative="Joanie Cunningham"
        )
        course = factories.CourseFactory()
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.DEGREE
        )
        product = factories.ProductFactory(
            courses=[],
            title="Graded product",
            certificate_definition=certificate_definition,
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Université X")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        order = factories.OrderFactory(product=product)
        certificate = factories.OrderCertificateFactory(order=order)

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
        self.assertRegex(document_text, "Certificate")
        self.assertRegex(document_text, rf"Certificate ID: {str(certificate.id)}")
        self.assertRegex(
            document_text, r"Joanie Cunningham.*University X.*Graded product"
        )

        with switch_language(product, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"Joanie Cunningham.*Université X")

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"Joanie Cunningham.*University X")

    def test_utils_issuers_generate_document_certificate_document(self):
        """
        The generated document in PDF bytes format should be rendered into the active language
        of the certificate's context. When we force the language to French, we should find
        translated strings into the given code language. By default, the language is in English,
        and the fallback language as well.
        """
        organization = factories.OrganizationFactory(title="University X")
        user = factories.UserFactory(first_name="Joanie Cunningham")
        course = factories.CourseFactory(title="Course with attestation")
        enrollment = factories.EnrollmentFactory(user=user, course_run__course=course)
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.CERTIFICATE
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Université X")
        course.translations.create(
            language_code="fr-fr", title="Cours avec attestation"
        )

        certificate = factories.EnrollmentCertificateFactory(
            certificate_definition=certificate_definition,
            enrollment=enrollment,
            organization=organization,
        )

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )
        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
        self.assertRegex(document_text, "ATTESTATION OF ACHIEVEMENT")
        self.assertRegex(
            document_text, r"Joanie Cunningham.*Course with attestation.*University X"
        )

        with switch_language(course, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Joanie Cunningham.*Cours avec attestation.*Université X",
            )

        with switch_language(course, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Joanie Cunningham.*Course with attestation.*University X",
            )
