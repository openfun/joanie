"""Tests for the Certificate API"""

import uuid
from http import HTTPStatus
from io import BytesIO
from unittest import mock

from pdfminer.high_level import extract_text as pdf_extract_text
from rest_framework.pagination import PageNumberPagination

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class CertificateApiTest(BaseAPITestCase):
    """Certificate API test case."""

    maxDiff = None

    def test_api_certificate_read_list_anonymous(self):
        """It should not be possible to retrieve the list of certificates for anonymous user"""
        factories.OrderCertificateFactory.create_batch(2)
        response = self.client.get("/api/v1.0/certificates/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_list_authenticated(self, _mock_thumbnail):
        """
        When an authenticated user retrieves the list of certificates,
        it should return only his/hers. In this context, we create for the user:
        - 2 certificates linked to 2 distinct orders.
        - 3 certificates linked to 2 distinct enrollments.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Creates 5 random orders that has certificates not owned by the user
        factories.OrderCertificateFactory.create_batch(5)
        # 1st certificate linked to an order
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)
        # 2nd certificate linked to an enrollment
        enrollment_1 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_1 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_1
        )
        # 3rd certificate linked to an enrollment
        enrollment_2 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_2 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_2
        )
        # 4th certificate linked to an order
        other_enrollment = factories.EnrollmentFactory(user=user)
        other_order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                courses=[other_enrollment.course_run.course],
            ),
            course=None,
            enrollment=other_enrollment,
        )
        other_certificate = factories.OrderCertificateFactory(order=other_order)
        # 5th certificate linked to an enrollment
        enrollment_3 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_3 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_3
        )

        with self.assertNumQueries(4):
            response = self.client.get(
                "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "count": 5,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(certificate_enrollment_3.id),
                        "certificate_definition": {
                            "description": "",
                            "name": certificate_enrollment_3.certificate_definition.name,
                            "title": certificate_enrollment_3.certificate_definition.title,
                        },
                        "issued_on": format_date(certificate_enrollment_3.issued_on),
                        "order": None,
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": enrollment_3.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(enrollment_3.course_run.course.id),
                                    "title": enrollment_3.course_run.course.title,
                                },
                                "end": format_date(enrollment_3.course_run.end),
                                "enrollment_end": format_date(
                                    enrollment_3.course_run.enrollment_end
                                ),
                                "enrollment_start": format_date(
                                    enrollment_3.course_run.enrollment_start
                                ),
                                "id": str(enrollment_3.course_run.id),
                                "languages": enrollment_3.course_run.languages,
                                "resource_link": enrollment_3.course_run.resource_link,
                                "start": format_date(enrollment_3.course_run.start),
                                "state": {
                                    "call_to_action": enrollment_3.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": format_date(
                                        enrollment_3.course_run.state.get("datetime")
                                    ),
                                    "priority": enrollment_3.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": enrollment_3.course_run.state.get("text"),
                                },
                                "title": enrollment_3.course_run.title,
                            },
                            "created_on": format_date(enrollment_3.created_on),
                            "id": str(enrollment_3.id),
                            "is_active": enrollment_3.is_active,
                            "state": enrollment_3.state,
                            "was_created_by_order": enrollment_3.was_created_by_order,
                        },
                    },
                    {
                        "id": str(other_certificate.id),
                        "certificate_definition": {
                            "description": other_certificate.certificate_definition.description,
                            "name": other_certificate.certificate_definition.name,
                            "title": other_certificate.certificate_definition.title,
                        },
                        "issued_on": format_date(other_certificate.issued_on),
                        "enrollment": None,
                        "order": {
                            "id": str(other_order.id),
                            "course": None,
                            "enrollment": {
                                "course_run": {
                                    "course": {
                                        "code": other_enrollment.course_run.course.code,
                                        "cover": "_this_field_is_mocked",
                                        "id": str(
                                            other_enrollment.course_run.course.id
                                        ),
                                        "title": other_enrollment.course_run.course.title,
                                    },
                                    "end": format_date(other_enrollment.course_run.end),
                                    "enrollment_end": format_date(
                                        other_enrollment.course_run.enrollment_end
                                    ),
                                    "enrollment_start": format_date(
                                        other_enrollment.course_run.enrollment_start
                                    ),
                                    "id": str(other_enrollment.course_run.id),
                                    "languages": other_enrollment.course_run.languages,
                                    "resource_link": other_enrollment.course_run.resource_link,
                                    "start": format_date(
                                        other_enrollment.course_run.start
                                    ),
                                    "state": {
                                        "call_to_action": other_enrollment.course_run.state.get(
                                            "call_to_action"
                                        ),
                                        "datetime": format_date(
                                            other_enrollment.course_run.state.get(
                                                "datetime"
                                            )
                                        ),
                                        "priority": other_enrollment.course_run.state.get(
                                            "priority"
                                        ),
                                        "text": other_enrollment.course_run.state.get(
                                            "text"
                                        ),
                                    },
                                    "title": other_enrollment.course_run.title,
                                },
                                "created_on": format_date(other_enrollment.created_on),
                                "id": str(other_enrollment.id),
                                "is_active": other_enrollment.is_active,
                                "state": other_enrollment.state,
                                "was_created_by_order": other_enrollment.was_created_by_order,
                            },
                            "organization": {
                                "id": str(other_order.organization.id),
                                "code": other_order.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": other_order.organization.title,
                                "address": None,
                                "enterprise_code": other_order.organization.enterprise_code,
                                "activity_category_code": (
                                    other_order.organization.activity_category_code
                                ),
                                "contact_email": other_order.organization.contact_email,
                                "contact_phone": other_order.organization.contact_phone,
                                "dpo_email": other_order.organization.dpo_email,
                            },
                            "owner_name": other_certificate.order.owner.username,
                            "product_title": other_certificate.order.product.title,
                        },
                    },
                    {
                        "id": str(certificate_enrollment_2.id),
                        "certificate_definition": {
                            "description": (
                                certificate_enrollment_2.certificate_definition.description
                            ),
                            "name": certificate_enrollment_2.certificate_definition.name,
                            "title": certificate_enrollment_2.certificate_definition.title,
                        },
                        "issued_on": format_date(certificate_enrollment_2.issued_on),
                        "order": None,
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": enrollment_2.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(enrollment_2.course_run.course.id),
                                    "title": enrollment_2.course_run.course.title,
                                },
                                "end": format_date(enrollment_2.course_run.end),
                                "enrollment_end": format_date(
                                    enrollment_2.course_run.enrollment_end
                                ),
                                "enrollment_start": format_date(
                                    enrollment_2.course_run.enrollment_start
                                ),
                                "id": str(enrollment_2.course_run.id),
                                "languages": enrollment_2.course_run.languages,
                                "resource_link": enrollment_2.course_run.resource_link,
                                "start": format_date(enrollment_2.course_run.start),
                                "state": {
                                    "call_to_action": enrollment_2.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": format_date(
                                        enrollment_2.course_run.state.get("datetime")
                                    ),
                                    "priority": enrollment_2.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": enrollment_2.course_run.state.get("text"),
                                },
                                "title": enrollment_2.course_run.title,
                            },
                            "created_on": format_date(enrollment_2.created_on),
                            "id": str(enrollment_2.id),
                            "is_active": enrollment_2.is_active,
                            "state": enrollment_2.state,
                            "was_created_by_order": enrollment_2.was_created_by_order,
                        },
                    },
                    {
                        "id": str(certificate_enrollment_1.id),
                        "certificate_definition": {
                            "description": "",
                            "name": certificate_enrollment_1.certificate_definition.name,
                            "title": certificate_enrollment_1.certificate_definition.title,
                        },
                        "issued_on": format_date(certificate_enrollment_1.issued_on),
                        "order": None,
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": enrollment_1.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(enrollment_1.course_run.course.id),
                                    "title": enrollment_1.course_run.course.title,
                                },
                                "end": format_date(enrollment_1.course_run.end),
                                "enrollment_end": format_date(
                                    enrollment_1.course_run.enrollment_end
                                ),
                                "enrollment_start": format_date(
                                    enrollment_1.course_run.enrollment_start
                                ),
                                "id": str(enrollment_1.course_run.id),
                                "languages": enrollment_1.course_run.languages,
                                "resource_link": enrollment_1.course_run.resource_link,
                                "start": format_date(enrollment_1.course_run.start),
                                "state": {
                                    "call_to_action": enrollment_1.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": format_date(
                                        enrollment_1.course_run.state.get("datetime")
                                    ),
                                    "priority": enrollment_1.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": enrollment_1.course_run.state.get("text"),
                                },
                                "title": enrollment_1.course_run.title,
                            },
                            "created_on": format_date(enrollment_1.created_on),
                            "id": str(enrollment_1.id),
                            "is_active": enrollment_1.is_active,
                            "state": enrollment_1.state,
                            "was_created_by_order": enrollment_1.was_created_by_order,
                        },
                    },
                    {
                        "id": str(certificate.id),
                        "certificate_definition": {
                            "description": certificate.certificate_definition.description,
                            "name": certificate.certificate_definition.name,
                            "title": certificate.certificate_definition.title,
                        },
                        "issued_on": format_date(certificate.issued_on),
                        "enrollment": None,
                        "order": {
                            "id": str(order.id),
                            "course": {
                                "id": str(order.course.id),
                                "code": order.course.code,
                                "title": order.course.title,
                                "cover": "_this_field_is_mocked",
                            },
                            "enrollment": None,
                            "organization": {
                                "id": str(order.organization.id),
                                "code": order.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": order.organization.title,
                                "address": None,
                                "enterprise_code": order.organization.enterprise_code,
                                "activity_category_code": (
                                    order.organization.activity_category_code
                                ),
                                "contact_email": order.organization.contact_email,
                                "contact_phone": order.organization.contact_phone,
                                "dpo_email": order.organization.dpo_email,
                            },
                            "owner_name": certificate.order.owner.username,
                            "product_title": certificate.order.product.title,
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_authenticated_from_an_order(self, _mock_thumbnail):
        """
        An authenticated user should only be able to retrieve a certificate
        only if he/she owns it when it is linked to an order.
        """
        not_owned_certificate = factories.OrderCertificateFactory()
        user = factories.UserFactory()
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)
        address_organization = factories.OrganizationAddressFactory(
            organization=certificate.order.organization, is_main=True, is_reusable=True
        )
        token = self.generate_token_from_user(user)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Not found."})

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "id": str(certificate.id),
                "certificate_definition": {
                    "description": certificate.certificate_definition.description,
                    "name": certificate.certificate_definition.name,
                    "title": certificate.certificate_definition.title,
                },
                "issued_on": format_date(certificate.issued_on),
                "enrollment": None,
                "order": {
                    "id": str(certificate.order.id),
                    "course": {
                        "id": str(certificate.order.course.id),
                        "code": certificate.order.course.code,
                        "title": certificate.order.course.title,
                        "cover": "_this_field_is_mocked",
                    },
                    "enrollment": None,
                    "organization": {
                        "id": str(certificate.order.organization.id),
                        "code": certificate.order.organization.code,
                        "logo": "_this_field_is_mocked",
                        "title": certificate.order.organization.title,
                        "address": {
                            "id": str(address_organization.id),
                            "address": address_organization.address,
                            "city": address_organization.city,
                            "postcode": address_organization.postcode,
                            "country": address_organization.country,
                            "first_name": address_organization.first_name,
                            "last_name": address_organization.last_name,
                            "title": address_organization.title,
                            "is_main": address_organization.is_main,
                        },
                        "enterprise_code": certificate.order.organization.enterprise_code,
                        "activity_category_code": (
                            certificate.order.organization.activity_category_code
                        ),
                        "contact_email": certificate.order.organization.contact_email,
                        "contact_phone": certificate.order.organization.contact_phone,
                        "dpo_email": certificate.order.organization.dpo_email,
                    },
                    "owner_name": certificate.order.owner.username,
                    "product_title": certificate.order.product.title,
                },
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_authenticated_from_an_enrollment(
        self, _mock_thumbnail
    ):
        """
        An authenticated user should only be able to retrieve a certificate
        only if he/she owns it when it is linked to an enrollment.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        enrollment_1 = factories.EnrollmentFactory()
        not_owned_certificate = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_1
        )
        enrollment_2 = factories.EnrollmentFactory(user=user)
        owned_certificate_enrollment = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_2
        )
        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Not found."})

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{owned_certificate_enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "id": str(owned_certificate_enrollment.id),
                "certificate_definition": {
                    "description": owned_certificate_enrollment.certificate_definition.description,
                    "name": owned_certificate_enrollment.certificate_definition.name,
                    "title": owned_certificate_enrollment.certificate_definition.title,
                },
                "issued_on": format_date(owned_certificate_enrollment.issued_on),
                "order": None,
                "enrollment": {
                    "course_run": {
                        "course": {
                            "code": enrollment_2.course_run.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(enrollment_2.course_run.course.id),
                            "title": enrollment_2.course_run.course.title,
                        },
                        "end": format_date(enrollment_2.course_run.end),
                        "enrollment_end": format_date(
                            enrollment_2.course_run.enrollment_end
                        ),
                        "enrollment_start": format_date(
                            enrollment_2.course_run.enrollment_start
                        ),
                        "id": str(enrollment_2.course_run.id),
                        "languages": enrollment_2.course_run.languages,
                        "resource_link": enrollment_2.course_run.resource_link,
                        "start": format_date(enrollment_2.course_run.start),
                        "state": {
                            "call_to_action": enrollment_2.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": format_date(
                                enrollment_2.course_run.state.get("datetime")
                            ),
                            "priority": enrollment_2.course_run.state.get("priority"),
                            "text": enrollment_2.course_run.state.get("text"),
                        },
                        "title": enrollment_2.course_run.title,
                    },
                    "created_on": format_date(enrollment_2.created_on),
                    "id": str(enrollment_2.id),
                    "is_active": enrollment_2.is_active,
                    "state": enrollment_2.state,
                    "was_created_by_order": enrollment_2.was_created_by_order,
                },
            },
        )

    def test_api_certificate_download_anonymous(self):
        """
        An anonymous user should not be able to download a certificate.
        """
        certificate = factories.OrderCertificateFactory()

        response = self.client.get(f"/api/v1.0/certificates/{certificate.id}/download/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_download_authenticated_order(self):
        """
        An authenticated user should be able to download a certificate
        linked to an order only he/she owns it.
        """
        not_owned_certificate = factories.OrderCertificateFactory()
        user = factories.UserFactory()
        certificate_definition = factories.CertificateDefinitionFactory(
            template=enums.DEGREE
        )
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

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertDictEqual(
            response.json(),
            {"detail": f"No certificate found with id {not_owned_certificate.id}."},
        )

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={certificate.id}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"Certificate")

    def test_api_certificate_download_authenticated_enrollment(self):
        """
        An authenticated user should be able to download a certificate
        linked to an enrollment only he/she owns it.
        """
        not_owned_certificate = factories.EnrollmentCertificateFactory()
        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(user=user)
        certificate = factories.EnrollmentCertificateFactory(
            enrollment=enrollment, certificate_definition__template=enums.CERTIFICATE
        )

        token = self.generate_token_from_user(user)

        # - Try to retrieve a not owned certificate should return a 404
        response = self.client.get(
            f"/api/v1.0/certificates/{not_owned_certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertDictEqual(
            response.json(),
            {"detail": f"No certificate found with id {not_owned_certificate.id}."},
        )

        # - Try to retrieve an owned certificate should return the certificate id
        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={certificate.id}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"ATTESTATION OF ACHIEVEMENT")

    @mock.patch(
        "joanie.core.models.Certificate.get_document_context", side_effect=ValueError
    )
    def test_api_certificate_download_unprocessable_entity(self, _):
        """
        If the server is not able to create the certificate document, it should return
        a 422 error.
        """
        user = factories.UserFactory()
        certificate = factories.OrderCertificateFactory(order__owner=user)

        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/certificates/{certificate.id}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
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
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        self.assertDictEqual(response.json(), {"detail": 'Method "POST" not allowed.'})

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
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        self.assertDictEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

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
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        self.assertDictEqual(
            response.json(), {"detail": 'Method "DELETE" not allowed.'}
        )
