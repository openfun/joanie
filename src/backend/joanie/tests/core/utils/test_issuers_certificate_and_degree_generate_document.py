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
            title="University X",
            representative="Joanie Cunningham",
            representative_profession="Head of the Life long learning department",
        )
        course = factories.CourseFactory(organizations=[organization])
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.DEGREE
        )
        product = factories.ProductFactory(
            courses=[course],
            title="Graded product",
            certificate_definition=certificate_definition,
        )

        # - Add French translations
        organization.translations.create(language_code="fr-fr", title="Université X")
        product.translations.create(language_code="fr-fr", title="Produit certifiant")

        owner = factories.UserFactory(first_name="Richie Cunningham")
        order = factories.OrderFactory(product=product, owner=owner)
        certificate = factories.OrderCertificateFactory(order=order)

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
        self.assertRegex(document_text, "Certificate")
        self.assertRegex(
            document_text, f"Issued on {certificate.issued_on.strftime('%m/%d/%Y')}"
        )
        self.assertRegex(document_text, r"Richie Cunningham.*Graded product")
        self.assertRegex(
            document_text,
            r"University X.*Joanie Cunningham.*Head of the Life long learning department",
        )
        self.assertRegex(
            document_text, rf"https://example.com/en-us/certificates/{certificate.id}"
        )

        with switch_language(product, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Université X.*Joanie Cunningham.*Head of the Life long learning department",
            )
            self.assertRegex(
                document_text,
                rf"https://example.com/fr-fr/certificates/{certificate.id}",
            )

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"University X.*Joanie Cunningham.*Head of the Life long learning department",
            )
            self.assertRegex(
                document_text,
                rf"https://example.com/en-us/certificates/{certificate.id}",
            )

    def test_utils_issuers_generate_document_certificate_document(self):
        """
        The generated document in PDF bytes format should be rendered into the active language
        of the certificate's context. When we force the language to French, we should find
        translated strings into the given code language. By default, the language is in English,
        and the fallback language as well.
        """
        org_1 = factories.OrganizationFactory(title="University X")
        org_2 = factories.OrganizationFactory(title="University Y")
        user = factories.UserFactory(first_name="Joanie Cunningham")
        course = factories.CourseFactory(
            title="Course with attestation", organizations=[org_1, org_2]
        )
        enrollment = factories.EnrollmentFactory(user=user, course_run__course=course)
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.CERTIFICATE
        )

        # - Add French translations
        org_1.translations.create(language_code="fr-fr", title="Université X")
        org_2.translations.create(language_code="fr-fr", title="Université Y")
        course.translations.create(
            language_code="fr-fr", title="Cours avec attestation"
        )

        certificate = factories.EnrollmentCertificateFactory(
            certificate_definition=certificate_definition,
            enrollment=enrollment,
        )

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )
        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
        self.assertRegex(document_text, "ATTESTATION OF ACHIEVEMENT")
        self.assertRegex(
            document_text,
            r"Joanie Cunningham.*Course with attestation.*University Y and University X",
        )
        self.assertRegex(
            document_text,
            (
                r"The current document is not a degree or diploma and "
                r"does not award credits \(ECTS\)\."
                r" It does not certify that the learner was registered with "
                r"University Y and University X\."
                r" The learner's identity has not been verified\."
            ),
        )

        with switch_language(course, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Joanie Cunningham.*Cours avec attestation.*Université Y et Université X",
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
                r"Joanie Cunningham.*Course with attestation.*University Y and University X",
            )
