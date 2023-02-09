"""Tests for the Certificate API"""
import json
import uuid
from io import BytesIO
from unittest import mock

from pdfminer.high_level import extract_text as pdf_extract_text
from rest_framework.pagination import PageNumberPagination

from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE
from joanie.core.factories import (
    CertificateDefinitionFactory,
    CertificateFactory,
    CourseProductRelationFactory,
    OrderFactory,
    OrganizationFactory,
    ProductFactory,
    UserFactory,
)
from joanie.tests.base import BaseAPITestCase


class CertificateApiTest(BaseAPITestCase):
    """Certificate API test case."""

    def test_api_certificate_read_list_anonymous(self):
        """It should not be possible to retrieve the list of certificates for anonymous user"""
        CertificateFactory.create_batch(2)
        response = self.client.get("/api/v1.0/certificates/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_read_list_authenticated(self):
        """
        When an authenticated user retrieves the list of certificates,
        it should return only his/hers.
        """
        CertificateFactory.create_batch(5)
        user = UserFactory()
        order = OrderFactory(
            owner=user, product=ProductFactory(type=PRODUCT_TYPE_CERTIFICATE)
        )
        certificate = CertificateFactory(order=order)

        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"id": str(certificate.id)}],
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_certificate_read_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = UserFactory()
        token = self.get_user_token(user.username)

        orders = [
            OrderFactory(
                owner=user, product=ProductFactory(type=PRODUCT_TYPE_CERTIFICATE)
            )
            for _ in range(3)
        ]
        certificates = [CertificateFactory(order=order) for order in orders]
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
        certificate = CertificateFactory()

        response = self.client.get(f"/api/v1.0/certificates/{certificate.id}/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_read_authenticated(self):
        """
        An authenticated user should only be able to retrieve a certificate
        only if he/she owns it.
        """
        not_owned_certificate = CertificateFactory()
        user = UserFactory()
        order = OrderFactory(
            owner=user, product=ProductFactory(type=PRODUCT_TYPE_CERTIFICATE)
        )
        certificate = CertificateFactory(order=order)

        token = self.get_user_token(user.username)

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
        self.assertEqual(content, {"id": str(certificate.id)})

    def test_api_certificate_download_anonymous(self):
        """
        An anonymous user should not be able to download a certificate.
        """
        certificate = CertificateFactory()

        response = self.client.get(f"/api/v1.0/certificates/{certificate.id}/download/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_download_authenticated(self):
        """
        An authenticated user should be able to download a certificate
        only he/she owns it.
        """
        not_owned_certificate = CertificateFactory()
        user = UserFactory()
        certificate_definition = CertificateDefinitionFactory()
        product = ProductFactory(
            title="Graded product",
            type=PRODUCT_TYPE_CERTIFICATE,
            certificate_definition=certificate_definition,
        )
        order = OrderFactory(
            owner=user, product=product, course=product.courses.first()
        )
        certificate = CertificateFactory(order=order)

        token = self.get_user_token(user.username)

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
        user = UserFactory()
        organization = OrganizationFactory(
            title="University X", representative="Joanie Cunningham", logo=None
        )

        product = ProductFactory(
            courses=[],
            title="Graded product",
            type=PRODUCT_TYPE_CERTIFICATE,
        )
        CourseProductRelationFactory(product=product, organizations=[organization])

        order = OrderFactory(product=product, organization=organization, owner=user)
        certificate = CertificateFactory(order=order)

        token = self.get_user_token(user.username)

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
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
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
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        certificate = CertificateFactory()
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
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        certificate = CertificateFactory()
        response = self.client.delete(
            f"/api/v1.0/certificates/{certificate.id}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "DELETE" not allowed.'})
