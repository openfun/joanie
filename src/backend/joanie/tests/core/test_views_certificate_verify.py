"""CertificateVerificationView test suite."""

import uuid
from http import HTTPStatus

from django.test import TestCase
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

    def test_views_certificate_verification_view_with_non_degree_certificate(self):
        """
        Only degree certificates should be verified otherwise a 404 should be returned.
        """
        certificate = factories.EnrollmentCertificateFactory(
            certificate_definition__template=enums.CERTIFICATE
        )

        url = reverse(
            "certificate-verification", kwargs={"certificate_id": certificate.id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_views_certificate_verification_view(self):
        """
        CertificateVerificationView should return a 200 if the certificate id is known
        and the certificate is a degree certificate.
        """
        owner = factories.UserFactory(first_name="John Doe")
        organization = factories.OrganizationFactory(title="Test Organization")
        degree_definition = factories.CertificateDefinitionFactory(
            template=enums.DEGREE
        )
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__certificate_definition=degree_definition,
            course__organizations=[organization],
        )
        order = factories.OrderFactory(
            product=relation.product, course=relation.course, owner=owner
        )
        certificate = factories.OrderCertificateFactory(order=order)
        self.assertEqual(certificate.certificate_definition.template, enums.DEGREE)

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
            "Please compare information displayed "
            "on the certificate below with yours.",
        )

        pdf_overview = html.cssselect("iframe")
        self.assertRegex(pdf_overview[0].attrib["src"], "^data:application/pdf;base64,")
        self.assertRegex(pdf_overview[0].attrib["type"], "application/pdf")
