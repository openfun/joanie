"""Tests for the Certificate API"""

import uuid
from datetime import date, datetime, timezone
from http import HTTPStatus
from io import BytesIO
from unittest import mock

from pdfminer.high_level import extract_text as pdf_extract_text
from rest_framework.pagination import PageNumberPagination

from joanie.core import enums, factories
from joanie.core.models import Certificate
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase

# pylint: disable=too-many-lines


class CertificateApiTest(BaseAPITestCase):
    """Certificate API test case."""

    maxDiff = None

    @staticmethod
    def generate_certificate_created_on_and_issued_on(
        user, created_on=None, issued_on=None
    ):
        """
        Generate a certificate for a user with a specific `created_on` date and `issued_on` date
        """
        if created_on:
            created_on = datetime.combine(
                created_on, datetime.now().time(), tzinfo=timezone.utc
            )

        with mock.patch(
            "django.utils.timezone.now",
            return_value=created_on or datetime.now(),
        ):
            certificate = factories.OrderCertificateFactory(
                order=factories.OrderFactory(
                    owner=user, product=factories.ProductFactory()
                )
            )

        if issued_on:
            issued_on = datetime.combine(
                issued_on, datetime.now().time(), tzinfo=timezone.utc
            )
            # Using the update method to by pass the auto_now and editable is False parameters
            # on the field set on the model.
            Certificate.objects.filter(pk=certificate.id).update(issued_on=issued_on)
            certificate.refresh_from_db()

        return certificate

    def test_api_certificate_read_list_anonymous(self):
        """It should not be possible to retrieve the list of certificates for anonymous user"""
        factories.OrderCertificateFactory.create_batch(2)
        response = self.client.get("/api/v1.0/certificates/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_certificate_read_list_should_be_in_the_order_of_issued_on_field_value(
        self,
    ):
        """
        Authenticated user should get the list certificates owned in the following order : from
        the most recent to the oldest depending on the `issued_on` date value.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Create random other certificates not attached to the user
        factories.OrderCertificateFactory.create_batch(5)
        # Create the certificates of the user
        certificate_0 = self.generate_certificate_created_on_and_issued_on(
            user, date(2024, 11, 12), date(2024, 11, 28)
        )
        certificate_1 = self.generate_certificate_created_on_and_issued_on(
            user, date(2024, 11, 13), date(2024, 11, 22)
        )
        certificate_2 = self.generate_certificate_created_on_and_issued_on(
            user, date(2024, 11, 15), date(2024, 11, 24)
        )
        certificate_3 = self.generate_certificate_created_on_and_issued_on(
            user, date(2024, 11, 15), date(2024, 11, 26)
        )

        response = self.client.get(
            "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json().get("count"), 4)

        content = response.json().get("results")

        self.assertEqual(content[0]["id"], str(certificate_0.id))
        self.assertEqual(content[1]["id"], str(certificate_3.id))
        self.assertEqual(content[2]["id"], str(certificate_2.id))
        self.assertEqual(content[3]["id"], str(certificate_1.id))

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
        - 2 "certificate" certificates linked to 2 distinct enrollments.
        - 1 "degree" certificate linked to 1 distinct enrollments.

        By default only the certificates linked to the orders and
        legacy degrees linked to enrollment are returned
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Creates 5 random orders that has certificates not owned by the user
        factories.OrderCertificateFactory.create_batch(5)
        # 1st certificate linked to an order
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)
        # 2nd "degree" certificate linked to an enrollment
        enrollment_1 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_1 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_1,
            certificate_definition__template=enums.DEGREE,
        )
        # 3rd "certificate" certificate linked to an enrollment
        enrollment_2 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(
            enrollment=enrollment_2,
            certificate_definition__template=enums.CERTIFICATE,
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
        factories.EnrollmentCertificateFactory(
            enrollment=enrollment_3,
            certificate_definition__template=enums.CERTIFICATE,
        )

        with self.assertNumQueries(19):
            response = self.client.get(
                "/api/v1.0/certificates/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
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
                            "state": other_order.state,
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
                            "owner_name": other_certificate.order.owner.get_full_name(),
                            "product_title": other_certificate.order.product.title,
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
                            "state": order.state,
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
                            "owner_name": certificate.order.owner.get_full_name(),
                            "product_title": certificate.order.product.title,
                        },
                    },
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_list_filtered_by_order_type(self, _mock_thumbnail):
        """
        When an authenticated user retrieves the list of certificates,
        it should return only his/hers. In this context, we create for the user:
        - 2 certificates linked to 2 distinct orders.
        - 1 "degree" certificate linked to 1 distinct enrollment.
        - 2 "certificate" certificates linked to 2 distinct enrollments.

        filtered by order type, only the certificates linked to the orders are returned.
        Legacy certificates linked to an enrollment with a degree template should also be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Creates 5 random orders that has certificates not owned by the user
        factories.OrderCertificateFactory.create_batch(5)
        # 1st certificate linked to an order
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        certificate = factories.OrderCertificateFactory(order=order)
        # 2nd certificate (degree) linked to an enrollment
        enrollment_1 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_1 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_1, certificate_definition__template=enums.DEGREE
        )
        # 3rd certificate linked to an enrollment
        enrollment_2 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(
            enrollment=enrollment_2, certificate_definition__template=enums.CERTIFICATE
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
        factories.EnrollmentCertificateFactory(
            enrollment=enrollment_3, certificate_definition__template=enums.CERTIFICATE
        )

        with self.assertNumQueries(19):
            response = self.client.get(
                "/api/v1.0/certificates/?type=order",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        expected_results = [other_certificate, certificate_enrollment_1, certificate]

        self.assertDictEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(cert.id),
                        "certificate_definition": {
                            "description": cert.certificate_definition.description,
                            "name": cert.certificate_definition.name,
                            "title": cert.certificate_definition.title,
                        },
                        "issued_on": format_date(cert.issued_on),
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": cert.enrollment.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(cert.enrollment.course_run.course.id),
                                    "title": cert.enrollment.course_run.course.title,
                                },
                                "end": format_date(cert.enrollment.course_run.end),
                                "enrollment_end": format_date(
                                    cert.enrollment.course_run.enrollment_end
                                ),
                                "enrollment_start": format_date(
                                    cert.enrollment.course_run.enrollment_start
                                ),
                                "id": str(cert.enrollment.course_run.id),
                                "languages": cert.enrollment.course_run.languages,
                                "resource_link": cert.enrollment.course_run.resource_link,
                                "start": format_date(cert.enrollment.course_run.start),
                                "state": {
                                    "call_to_action": cert.enrollment.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": format_date(
                                        cert.enrollment.course_run.state.get("datetime")
                                    ),
                                    "priority": cert.enrollment.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": cert.enrollment.course_run.state.get(
                                        "text"
                                    ),
                                },
                                "title": cert.enrollment.course_run.title,
                            },
                            "created_on": format_date(cert.enrollment.created_on),
                            "id": str(cert.enrollment.id),
                            "is_active": cert.enrollment.is_active,
                            "state": cert.enrollment.state,
                            "was_created_by_order": cert.enrollment.was_created_by_order,
                        }
                        if cert.enrollment
                        else None,
                        "order": {
                            "id": str(cert.order.id),
                            "state": cert.order.state,
                            "course": {
                                "id": str(cert.order.course.id),
                                "code": cert.order.course.code,
                                "title": cert.order.course.title,
                                "cover": "_this_field_is_mocked",
                            }
                            if cert.order.course
                            else None,
                            "enrollment": {
                                "course_run": {
                                    "course": {
                                        "code": cert.order.enrollment.course_run.course.code,
                                        "cover": "_this_field_is_mocked",
                                        "id": str(
                                            cert.order.enrollment.course_run.course.id
                                        ),
                                        "title": cert.order.enrollment.course_run.course.title,
                                    },
                                    "end": format_date(
                                        cert.order.enrollment.course_run.end
                                    ),
                                    "enrollment_end": format_date(
                                        cert.order.enrollment.course_run.enrollment_end
                                    ),
                                    "enrollment_start": format_date(
                                        cert.order.enrollment.course_run.enrollment_start
                                    ),
                                    "id": str(cert.order.enrollment.course_run.id),
                                    "languages": cert.order.enrollment.course_run.languages,
                                    "resource_link": cert.order.enrollment.course_run.resource_link,
                                    "start": format_date(
                                        cert.order.enrollment.course_run.start
                                    ),
                                    "state": {
                                        "call_to_action": cert.order.enrollment.course_run.state.get(  # pylint: disable=line-too-long
                                            "call_to_action"
                                        ),
                                        "datetime": format_date(
                                            cert.order.enrollment.course_run.state.get(
                                                "datetime"
                                            )
                                        ),
                                        "priority": cert.order.enrollment.course_run.state.get(
                                            "priority"
                                        ),
                                        "text": cert.order.enrollment.course_run.state.get(
                                            "text"
                                        ),
                                    },
                                    "title": cert.order.enrollment.course_run.title,
                                },
                                "created_on": format_date(
                                    cert.order.enrollment.created_on
                                ),
                                "id": str(cert.order.enrollment.id),
                                "is_active": cert.order.enrollment.is_active,
                                "state": cert.order.enrollment.state,
                                "was_created_by_order": cert.order.enrollment.was_created_by_order,
                            }
                            if cert.order.enrollment
                            else None,
                            "organization": {
                                "id": str(cert.order.organization.id),
                                "code": cert.order.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": cert.order.organization.title,
                                "address": None,
                                "enterprise_code": cert.order.organization.enterprise_code,
                                "activity_category_code": (
                                    cert.order.organization.activity_category_code
                                ),
                                "contact_email": cert.order.organization.contact_email,
                                "contact_phone": cert.order.organization.contact_phone,
                                "dpo_email": cert.order.organization.dpo_email,
                            },
                            "owner_name": cert.order.owner.get_full_name(),
                            "product_title": cert.order.product.title,
                        }
                        if cert.order
                        else None,
                    }
                    for cert in expected_results
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_list_filtered_by_enrollment_type(
        self, _mock_thumbnail
    ):
        """
        When an authenticated user retrieves the list of certificates,
        it should return only his/hers. In this context, we create for the user:
        - 2 certificates linked to 2 distinct orders.
        - 2 "degree" certificates linked to 2 distinct enrollments.
        - 1 "certificate" certificates linked to 1 distinct enrollment.

        Filtered by enrollment type, only the certificates linked to the enrollments are returned.
        Legacy certificates linked to an enrollment with a degree template should not be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Creates 5 random orders that has certificates not owned by the user
        factories.OrderCertificateFactory.create_batch(5)
        # 1st certificate linked to an order
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        factories.OrderCertificateFactory(order=order)
        # 2nd certificate (certificate) linked to an enrollment
        enrollment_1 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_1 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_1,
            certificate_definition__template=enums.CERTIFICATE,
        )
        # 3rd certificate (degree) linked to an enrollment
        enrollment_2 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(
            enrollment=enrollment_2,
            certificate_definition__template=enums.DEGREE,
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
        factories.OrderCertificateFactory(order=other_order)
        # 5th certificate (degree) linked to an enrollment
        enrollment_3 = factories.EnrollmentFactory(user=user)
        certificate_enrollment_3 = factories.EnrollmentCertificateFactory(
            enrollment=enrollment_3,
            certificate_definition__template=enums.CERTIFICATE,
        )

        with self.assertNumQueries(8):
            response = self.client.get(
                "/api/v1.0/certificates/?type=enrollment",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "count": 2,
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
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_certificate_read_list_unknown_filter_type(self, _mock_thumbnail):
        """
        Using an unknown type should return an empty list.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Creates 5 random orders that has certificates not owned by the user
        factories.OrderCertificateFactory.create_batch(5)
        # 1st certificate linked to an order
        order = factories.OrderFactory(owner=user, product=factories.ProductFactory())
        factories.OrderCertificateFactory(order=order)
        # 2nd certificate linked to an enrollment
        enrollment_1 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(enrollment=enrollment_1)
        # 3rd certificate linked to an enrollment
        enrollment_2 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(enrollment=enrollment_2)
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
        factories.OrderCertificateFactory(order=other_order)
        # 5th certificate linked to an enrollment
        enrollment_3 = factories.EnrollmentFactory(user=user)
        factories.EnrollmentCertificateFactory(enrollment=enrollment_3)

        with self.assertNumQueries(0):
            response = self.client.get(
                "/api/v1.0/certificates/?type=foo", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

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
        self.assertDictEqual(
            response.json(), {"detail": "No Certificate matches the given query."}
        )

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
                    "state": certificate.order.state,
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
                    "owner_name": certificate.order.owner.get_full_name(),
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
        self.assertDictEqual(
            response.json(), {"detail": "No Certificate matches the given query."}
        )

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
            {"detail": "No Certificate matches the given query."},
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
            {"detail": "No Certificate matches the given query."},
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
