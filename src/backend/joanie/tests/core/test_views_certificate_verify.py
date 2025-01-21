# pylint: disable=too-many-locals
"""CertificateVerificationView test suite."""

import random
import uuid
from http import HTTPStatus

from django.test import TestCase, override_settings
from django.urls import reverse

import lxml

from joanie.core import enums, factories


class CertificateVerificationViewTestCase(TestCase):
    """
    The CertificateVerificationView test suite.
    """

    def test_views_certificate_verification_view_with_unknown_id(self):
        """
        CertificateVerificationView should return a 404 if the certificate id is unknown.
        """
        url = reverse(
            "certificate-verification", kwargs={"certificate_id": uuid.uuid4()}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_views_certificate_verification_view_allow_only_verifiable_certificates(
        self,
    ):
        """
        Only verifiable certificates should be allowed to be verified.
        Otherwise, a 404 should be returned.
        """
        templates = [name for name, _ in enums.CERTIFICATE_NAME_CHOICES]
        for template in templates:
            with self.subTest(f"Test {template} certificate", template=template):
                cert_definition = factories.CertificateDefinitionFactory(
                    template=template
                )
                certificate = factories.OrderCertificateFactory(
                    order__product__type=enums.PRODUCT_TYPE_CREDENTIAL,
                    order__product__certificate_definition=cert_definition,
                )

                url = reverse(
                    "certificate-verification",
                    kwargs={"certificate_id": certificate.id},
                )

                response = self.client.get(url)

                if template in enums.VERIFIABLE_CERTIFICATES:
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_views_certificate_verification_view(self):
        """
        CertificateVerificationView should render a web page proving
        the certificate is genuine.
        """
        template = random.choice(enums.VERIFIABLE_CERTIFICATES)
        owner = factories.UserFactory(first_name="John Doe")
        organization = factories.OrganizationFactory(title="Test Organization")
        degree_definition = factories.CertificateDefinitionFactory(template=template)
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__certificate_definition=degree_definition,
            course__organizations=[organization],
        )
        order = factories.OrderFactory(
            product=relation.product, course=relation.course, owner=owner
        )
        certificate = factories.OrderCertificateFactory(order=order)
        self.assertEqual(certificate.certificate_definition.template, template)

        url = reverse(
            "certificate-verification", kwargs={"certificate_id": certificate.id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        html = lxml.html.fromstring(response.content)

        title = html.cssselect(".content__information h1")
        self.assertEqual(title[0].text, "This certificate is genuine!")

        paragraphs = html.cssselect(".content__information p")
        self.assertEqual(
            paragraphs[0].text,
            "This certificate has been issued on "
            f"{certificate.issued_on.strftime('%m/%d/%Y')} "
            "to John Doe by Test Organization.",
        )
        self.assertEqual(
            paragraphs[1].text,
            "Please compare information displayed on the certificate below with yours.",
        )

        footer = html.cssselect(".footer__content")
        self.assertIn("Test Catalog", footer[0].text)
        footer_link = html.cssselect(".footer__content a")
        self.assertIn("https://richie.education", footer_link[0].text)

        pdf_overview = html.cssselect("iframe")
        self.assertRegex(pdf_overview[0].attrib["src"], "^data:application/pdf;base64,")
        self.assertRegex(pdf_overview[0].attrib["type"], "application/pdf")
