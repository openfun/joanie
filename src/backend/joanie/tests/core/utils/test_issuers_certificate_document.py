"""Test suite for utility method to generate document of Certificate/Degree in PDF bytes format."""

import os
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.template.exceptions import TemplateDoesNotExist
from django.test import TestCase

import pymupdf
from parler.utils.context import switch_language
from pdfminer.high_level import extract_text as pdf_extract_text
from PIL import Image, ImageChops, ImageStat

from joanie.core import enums, factories
from joanie.core.utils import issuers


def call_issuers_generate_document(name: str, context: dict, path: str):
    """
    Call generate document from issuers but add extra step to output the file
    for testing purposes.
    """
    context["creation_date"] = datetime(2025, 11, 18, 14, tzinfo=ZoneInfo("UTC"))
    pdf_bytes = issuers.generate_document(name, context)
    pdf_output_path = path + name + ".pdf"
    with open(pdf_output_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)
    return pdf_output_path


def generate_certificate(template: str):
    """
    Create a certificate object for a given template using test factories.
    Sets up organization, course, product, owner, and order for testing.
    Returns the generated Certificate instance.
    """
    organization = factories.OrganizationFactory(
        title="University X",
        representative="Joanie Cunningham",
        representative_profession="Head of the department",
    )
    course = factories.CourseFactory(
        organizations=[organization],
    )
    certificate_definition = factories.CertificateDefinitionFactory(template=template)
    product = factories.ProductFactory(
        courses=[course],
        title="Graded product",
        certificate_definition=certificate_definition,
        certification_level=None,
    )
    owner = factories.UserFactory(first_name="Joanie Cunningham")
    order = factories.OrderFactory(product=product, owner=owner)
    return factories.OrderCertificateFactory(
        id="717e8e20-11d3-4a28-af65-21bbbf7f4a1d",
        issued_on=datetime(2025, 11, 18, 14, tzinfo=ZoneInfo("UTC")),
        order=order,
    )


def convert_pdf_to_png(pdf_path: str):
    """
    Convert the first page of a PDF file into a PNG image at 150 DPI.
    Returns the path to the generated image.
    """
    generated_pdf = pymupdf.open(pdf_path)
    generated_pdf = generated_pdf.load_page(0)
    generated_image = generated_pdf.get_pixmap(dpi=150)
    generated_image_path = pdf_path.replace(".pdf", ".png")
    generated_image.save(generated_image_path)
    return generated_image_path


def compare_images(first_image: Image, second_image: Image, output_path: str):
    """
    Compare two images and save the difference image to the specified output path.
    Returns the average RMS difference between the images.
    """
    diff = ImageChops.difference(first_image, second_image)
    diff.save(output_path)
    rms = ImageStat.Stat(diff).rms
    tolerated_diff = sum(rms) / len(rms)
    return tolerated_diff


def clear_generated_files(base_path: str, certificate_name: str):
    """
    Remove the generated files from the output directory.
    """
    os.remove(base_path + certificate_name + ".png")
    os.remove(base_path + certificate_name + "_diff.png")


class UtilsIssuersCertificateGenerateDocumentTestCase(TestCase):
    """
    Test suite for utility method to generate document of Certificate in PDF bytes format.
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
        self.assertRegex(document_text, r"en-us")

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

            self.assertRegex(document_text, r"fr-fr")

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
            self.assertRegex(document_text, r"en-us")

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

    def test_utils_issuers_generate_document_certificate_unicamp_degree_document(self):
        """
        The generated document in PDF bytes format should be rendered into the active language
        of the certificate's context. The method `get_document_context` will prepare the data
        in the appropriate language.
        """
        organization = factories.OrganizationFactory(
            title="University X",
            representative="Joanie Cunningham",
            representative_profession="Head of the department",
        )
        course = factories.CourseFactory(organizations=[organization])
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.MICROCREDENTIAL_DEGREE_UNICAMP
        )
        skill1 = factories.SkillFactory(title="Skill 1")
        skill1.translations.create(language_code="fr-fr", title="Compétence 1")
        skill2 = factories.SkillFactory(title="Skill 2")
        skill2.translations.create(language_code="fr-fr", title="Compétence 2")
        teacher1 = factories.TeacherFactory(first_name="Teacher", last_name="1")
        teacher2 = factories.TeacherFactory(first_name="Teacher", last_name="2")
        product = factories.ProductFactory(
            courses=[course],
            title="Graded product",
            certificate_definition=certificate_definition,
            certification_level=8,
            skills=[skill1, skill2],
            teachers=[teacher1, teacher2],
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
        self.assertRegex(
            document_text,
            f"Issued on {certificate.issued_on.strftime('%-d %B %Y')} in France",
        )
        self.assertRegex(
            document_text,
            (
                r"Richie Cunningham"
                r"acquired the skills from the professional training:"
                r"Graded product"
            ),
        )
        self.assertRegex(
            document_text,
            r"Joanie.*Cunningham.*Head of the department.*University X",
        )
        self.assertRegex(
            document_text,
            (
                r"Teacher 1.*Educational coordinator.*"
                r"Teacher 2.*Educational coordinator"
            ),
        )
        self.assertRegex(
            document_text,
            r"Skill 1.*Skill 2",
        )
        self.assertRegex(
            document_text,
            r"Certification.*level.*8",
        )
        self.assertRegex(
            document_text, rf"https://example.com/en-us/certificates/{certificate.id}"
        )
        self.assertRegex(document_text, r"https://example.com/terms")
        self.assertRegex(document_text, r"en-us")

        with switch_language(product, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Joanie.*Cunningham.*Produit certifiant",
            )
            self.assertRegex(
                document_text,
                r"Joanie.*Cunningham.*Head of the department.*Université X",
            )
            self.assertRegex(
                document_text,
                rf"https://example.com/fr-fr/certificates/{certificate.id}",
            )
            self.assertRegex(
                document_text,
                r"Compétence 1.*Compétence 2",
            )
            self.assertRegex(document_text, r"fr-fr")

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(
                document_text,
                r"Joanie.*Cunningham.*Head of the department.*University X",
            )
            self.assertRegex(
                document_text,
                rf"https://example.com/en-us/certificates/{certificate.id}",
            )
            self.assertRegex(document_text, r"en-us")

    def test_utils_issuers_generate_document_certificate_unicamp_degree_document_without_certification_level(  # pylint: disable=line-too-long
        self,
    ):
        """
        In the Unicamp degree template if the certification level is None, this information should
        not be displayed in the document.
        """
        organization = factories.OrganizationFactory(
            title="University X",
            representative="Joanie Cunningham",
            representative_profession="Head of the Life long learning department",
        )
        course = factories.CourseFactory(organizations=[organization])
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.MICROCREDENTIAL_DEGREE_UNICAMP
        )

        product = factories.ProductFactory(
            courses=[course],
            title="Graded product",
            certificate_definition=certificate_definition,
            certification_level=None,
        )

        owner = factories.UserFactory(first_name="Richie Cunningham")
        order = factories.OrderFactory(product=product, owner=owner)
        certificate = factories.OrderCertificateFactory(order=order)

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
        self.assertRegex(
            document_text,
            (
                r"Richie Cunningham.*"
                r"acquired the skills from the professional training.*"
                r"Graded product"
            ),
        )
        self.assertNotRegex(
            document_text,
            r"Certification.*level",
        )
        self.assertRegex(document_text, r"en-us")

        with switch_language(product, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"fr-fr")

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"en-us")

    def test_utils_issuers_generate_document_microcredential_degree_default(self):
        """
        We should be able to generate a microcredential degree default template. The method
        `get_document_context` will prepare the data in the appropriate language.
        """
        certificate = generate_certificate(enums.MICROCREDENTIAL_DEGREE_DEFAULT)
        product = certificate.order.product

        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")

        self.assertRegex(
            document_text,
            (
                r"Joanie Cunningham.*"
                r"acquired the skills from the professional training.*"
                r"Graded product"
            ),
        )
        self.assertRegex(document_text, r"en-us")

        with switch_language(product, "fr-fr"):
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"fr-fr")

        with switch_language(product, "de-de"):
            # - Finally, unknown language should use the default language as fallback
            document = issuers.generate_document(
                name=certificate.certificate_definition.template,
                context=certificate.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(document)).replace("\n", "")
            self.assertRegex(document_text, r"en-us")

    def test_utils_issuers_verify_document_microcredential_degree_default_style(self):
        """
        When generating the template of the microcredential degree, the style of the document
        should match the original once.
        """
        base_path = settings.BASE_DIR + "/joanie/tests/core/utils/__diff__/"

        certificate = generate_certificate(
            template=enums.MICROCREDENTIAL_DEGREE_DEFAULT
        )

        pdf_path = call_issuers_generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
            path=base_path,
        )

        generated_image_path = convert_pdf_to_png(pdf_path)
        generated_image = Image.open(generated_image_path).convert("RGB")

        os.remove(base_path + certificate.certificate_definition.template + ".pdf")

        original_image = Image.open(
            base_path + certificate.certificate_definition.template + "_original.png"
        ).convert("RGB")

        self.assertEqual(generated_image.size, original_image.size)

        diff = compare_images(
            generated_image,
            original_image,
            base_path + certificate.certificate_definition.template + "_diff.png",
        )
        self.assertLessEqual(
            diff,
            1.5,
            f"""
            Test failed since the images are different, if you want to keep the new version use
            mv -f {base_path}microcredential_degree_default.png 
            {base_path}microcredential_degree_default_original.png 
            rm -f {base_path}microcredential_degree_default_diff.png
        """,
        )

        clear_generated_files(base_path, certificate.certificate_definition.template)

    def test_utils_issuers_verify_document_microcredential_degree_unicamp_style(self):
        """
        When generating the template of the microcredential degree, the style of the document
        should match the original once.
        """
        base_path = settings.BASE_DIR + "/joanie/tests/core/utils/__diff__/"

        certificate = generate_certificate(
            template=enums.MICROCREDENTIAL_DEGREE_UNICAMP
        )

        pdf_path = call_issuers_generate_document(
            name=certificate.certificate_definition.template,
            context=certificate.get_document_context(),
            path=base_path,
        )

        generated_image_path = convert_pdf_to_png(pdf_path)
        generated_image = Image.open(generated_image_path).convert("RGB")

        os.remove(base_path + certificate.certificate_definition.template + ".pdf")

        original_image = Image.open(
            base_path + certificate.certificate_definition.template + "_original.png"
        ).convert("RGB")

        self.assertEqual(generated_image.size, original_image.size)

        diff = compare_images(
            generated_image,
            original_image,
            base_path + certificate.certificate_definition.template + "_diff.png",
        )
        self.assertLessEqual(
            diff,
            1.5,
            f"""
            Test failed since the images are different, if you want to keep the new version use
            mv -f {base_path}microcredential_degree_unicamp.png 
            {base_path}microcredential_degree_unicamp_original.png 
            rm -f {base_path}microcredential_degree_unicamp_diff.png
        """,
        )

        clear_generated_files(base_path, certificate.certificate_definition.template)

    def test_utils_issuers_generate_document_template_does_not_exist(self):
        """If the template html and css don't exist, issuer generate document should fail"""
        certificate = factories.OrderCertificateFactory(order=factories.OrderFactory())

        with self.assertRaises(TemplateDoesNotExist) as context:
            issuers.generate_document(
                name="unicamp-degree",
                context=certificate.get_document_context(),
            )

        self.assertTrue(
            str(context.exception),
            "issuers/unicamp-degree.html",
        )
