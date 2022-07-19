"""Tests for the IssuedCertificate API"""
import json
import uuid
from io import BytesIO

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE
from joanie.core.factories import (
    CertificateFactory,
    IssuedCertificateFactory,
    OrderFactory,
    ProductFactory,
    UserFactory,
)
from joanie.tests.base import BaseAPITestCase


class IssuedCertificateApiTest(BaseAPITestCase):
    """IssuedCertificate API test case."""

    def test_api_certificate_read_list_anonymous(self):
        """It should not be possible to retrieve the list of certificates for anonymous user"""
        IssuedCertificateFactory.create_batch(2)
        response = self.client.get("/api/issued-certificates/")

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
        IssuedCertificateFactory.create_batch(5)
        user = UserFactory()
        order = OrderFactory(owner=user)
        certificate = IssuedCertificateFactory(order=order)

        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/issued-certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content, [{"id": str(certificate.uid)}])

    def test_api_certificate_read_anonymous(self):
        """
        An anonymous user should not be able to retrieve a certificate
        """
        certificate = IssuedCertificateFactory()

        response = self.client.get(f"/api/issued-certificates/{certificate.uid}/")

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
        not_owned_certificate = IssuedCertificateFactory()
        user = UserFactory()
        order = OrderFactory(owner=user)
        certificate = IssuedCertificateFactory(order=order)

        token = self.get_user_token(user.username)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/issued-certificates/{not_owned_certificate.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/issued-certificates/{certificate.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content, {"id": str(certificate.uid)})

    def test_api_certificate_download_anonymous(self):
        """
        An anonymous user should not be able to download a certificate.
        """
        certificate = IssuedCertificateFactory()

        response = self.client.get(
            f"/api/issued-certificates/{certificate.uid}/download/"
        )

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
        not_owned_certificate = IssuedCertificateFactory()
        user = UserFactory()
        certificate = CertificateFactory()
        product = ProductFactory(
            title="Graded product",
            type=PRODUCT_TYPE_CERTIFICATE,
            certificate=certificate,
        )
        order = OrderFactory(
            owner=user, product=product, course=product.courses.first()
        )
        certificate = IssuedCertificateFactory(order=order)

        token = self.get_user_token(user.username)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/issued-certificates/{not_owned_certificate.uid}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {
                "detail": f"No issued certificate found with uid {not_owned_certificate.uid}."
            },
        )

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/issued-certificates/{certificate.uid}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={certificate.uid}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"CERTIFICATE")

    def test_api_certificate_create(self):
        """
        Create a certificate should not be allowed even if user is admin
        """
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        response = self.client.post(
            "/api/issued-certificates/",
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
        certificate = IssuedCertificateFactory()
        response = self.client.put(
            f"/api/issued-certificates/{certificate.uid}/",
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
        certificate = IssuedCertificateFactory()
        response = self.client.delete(
            f"/api/issued-certificates/{certificate.uid}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "DELETE" not allowed.'})
