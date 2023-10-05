"""Tests for the Certificate API"""
import json
import uuid
from io import BytesIO
from unittest import mock

from pdfminer.high_level import extract_text as pdf_extract_text
from rest_framework.pagination import PageNumberPagination

from joanie.core import factories
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CertificateApiTest(BaseAPITestCase):
    """Certificate API test case."""

    def test_api_certificate_read_list_anonymous(self):
        """It should not be possible to retrieve the list of certificates for anonymous user"""
        factories.OrderCertificateFactory.create_batch(2)
        response = self.client.get("/api/v1.0/certificates/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_list_authenticated(self, _mock_thumbnail):
        """
        When an authenticated user retrieves the list of certificates,
        it should return only his/hers.
        """
        factories.OrderCertificateFactory.create_batch(5)
        user = factories.UserFactory()
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)

        token = self.generate_token_from_user(user)

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, 200)
        order = certificate.order
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(certificate.id),
                        "certificate_definition": {
                            "description": certificate.certificate_definition.description,
                            "name": certificate.certificate_definition.name,
                            "title": certificate.certificate_definition.title,
                        },
                        "issued_on": certificate.issued_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "order": {
                            "id": str(order.id),
                            "course": {
                                "id": str(order.course.id),
                                "code": order.course.code,
                                "title": order.course.title,
                                "cover": "_this_field_is_mocked",
                            },
                            "organization": {
                                "id": str(order.organization.id),
                                "code": order.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": order.organization.title,
                            },
                        },
                    },
                ],
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_certificate_read_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        orders = [
            factories.OrderFactory(owner=user, product=factories.ProductFactory())
            for _ in range(3)
        ]
        certificates = [
            factories.OrderCertificateFactory(order=order) for order in orders
        ]
        certificate_ids = [str(certificate.id) for certificate in certificates]

        response = self.client.get(
            "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"], "http://testserver/api/v1.0/certificates/?page=2"
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            certificate_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/certificates/?page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"], "http://testserver/api/v1.0/certificates/"
        )

        self.assertEqual(len(content["results"]), 1)
        certificate_ids.remove(content["results"][0]["id"])
        self.assertEqual(certificate_ids, [])

    def test_api_certificate_read_anonymous(self):
        """
        An anonymous user should not be able to retrieve a certificate
        """
        certificate = factories.OrderCertificateFactory()

        response = self.client.get(f"/api/v1.0/certificates/{certificate.id}/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_authenticated(self, _mock_thumbnail):
        """
        An authenticated user should only be able to retrieve a certificate
        only if he/she owns it.
        """
        not_owned_certificate = factories.OrderCertificateFactory()
        user = factories.UserFactory()
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)

        token = self.generate_token_from_user(user)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {
                "id": str(certificate.id),
                "certificate_definition": {
                    "description": certificate.certificate_definition.description,
                    "name": certificate.certificate_definition.name,
                    "title": certificate.certificate_definition.title,
                },
                "issued_on": certificate.issued_on.isoformat().replace("+00:00", "Z"),
                "order": {
                    "id": str(certificate.order.id),
                    "course": {
                        "id": str(certificate.order.course.id),
                        "code": certificate.order.course.code,
                        "title": certificate.order.course.title,
                        "cover": "_this_field_is_mocked",
                    },
                    "organization": {
                        "id": str(certificate.order.organization.id),
                        "code": certificate.order.organization.code,
                        "logo": "_this_field_is_mocked",
                        "title": certificate.order.organization.title,
                    },
                },
            },
        )

    def test_api_certificate_download_anonymous(self):
        """
        An anonymous user should not be able to download a certificate.
        """
        certificate = factories.OrderCertificateFactory()

        response = self.client.get(f"/api/v1.0/certificates/{certificate.id}/download/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_download_authenticated_order(self):
        """
        An authenticated user should be able to download a certificate
        linked to an order only he/she owns it.
        """
        not_owned_certificate = factories.OrderCertificateFactory()
        user = factories.UserFactory()
        certificate_definition = factories.CertificateDefinitionFactory()
        product = factories.ProductFactory(
            title="Graded product",
            certificate_definition=certificate_definition,
        )
        order = factories.OrderFactory(
            owner=user, product=product, course=product.courses.first()
        )
        certificate = factories.OrderCertificateFactory(order=order)

        token = self.generate_token_from_user(user)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": f"No certificate found with id {not_owned_certificate.id}."},
        )

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={certificate.id}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"CERTIFICATE")

    def test_api_certificate_download_authenticated_enrollment(self):
        """
        An authenticated user should be able to download a certificate
        linked to an enrollment only he/she owns it.
        """
        not_owned_certificate = factories.EnrollmentCertificateFactory()
        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(user=user)
        certificate = factories.EnrollmentCertificateFactory(enrollment=enrollment)

        token = self.generate_token_from_user(user)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": f"No certificate found with id {not_owned_certificate.id}."},
        )

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={certificate.id}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"CERTIFICATE")

    def test_api_certificate_download_unprocessable_entity(self):
        """
        If the server is not able to create the certificate document, it should return
        a 422 error.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(
            title="University X", representative="Joanie Cunningham", logo=None
        )

        product = factories.ProductFactory(
            courses=[],
            title="Graded product",
        )
        factories.CourseProductRelationFactory(
            product=product, organizations=[organization]
        )

        order = factories.OrderFactory(
            product=product, organization=organization, owner=user
        )
        certificate = factories.OrderCertificateFactory(order=order)

        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"detail": f"Unable to generate certificate {str(certificate.id)}."},
        )

    def test_api_certificate_create(self):
        """
        Create a certificate should not be allowed even if user is admin
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        token = self.generate_token_from_user(user)
        response = self.client.post(
            "/api/v1.0/certificates/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

    def test_api_certificate_update(self):
        """
        Update a certificate should not be allowed even if user is admin
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        token = self.generate_token_from_user(user)
        certificate = factories.OrderCertificateFactory()
        response = self.client.put(
            f"/api/v1.0/certificates/{certificate.id}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

    def test_api_certificate_delete(self):
        """
        Delete a certificate should not be allowed even if user is admin
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        token = self.generate_token_from_user(user)
        certificate = factories.OrderCertificateFactory()
        response = self.client.delete(
            f"/api/v1.0/certificates/{certificate.id}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "DELETE" not allowed.'})
