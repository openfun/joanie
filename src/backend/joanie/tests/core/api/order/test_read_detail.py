"""Tests for the Order read detail API."""

from datetime import datetime
from http import HTTPStatus
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache

from joanie.core import factories
from joanie.core.enums import ORDER_STATE_VALIDATED
from joanie.core.models import CourseState
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class OrderReadApiTest(BaseAPITestCase):
    """Test the API of the Order read detail."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_read_detail_anonymous(self):
        """Anonymous users should not be allowed to retrieve an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.get(f"/api/v1.0/orders/{order.id}/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_detail_authenticated_owner(self, _mock_thumbnail):
        """Authenticated users should be allowed to retrieve an order they own."""
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        factories.CourseRunFactory(
            course=target_courses[0], state=CourseState.ONGOING_CLOSED
        )
        factories.CourseRunFactory(
            course=target_courses[1], state=CourseState.ONGOING_OPEN
        )
        product = factories.ProductFactory(target_courses=target_courses, price=1000)
        order = factories.OrderFactory(
            product=product,
            owner=owner,
            contract=factories.ContractFactory(
                submitted_for_signature_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
                student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            ),
            state=ORDER_STATE_VALIDATED,
        )
        # Generate payment schedule
        # breakpoint()
        order.generate_schedule()

        organization_address = order.organization.addresses.filter(is_main=True).first()
        token = self.generate_token_from_user(owner)

        with self.assertNumQueries(9):
            response = self.client.get(
                f"/api/v1.0/orders/{order.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": order.course.code,
                    "id": str(order.course.id),
                    "title": order.course.title,
                    "cover": "_this_field_is_mocked",
                },
                "payment_schedule": [
                    {
                        "amount": float(installment["amount"]),
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": format_date(installment["due_date"]),
                        "state": installment["state"],
                    }
                    for installment in order.payment_schedule
                ]
                if order.payment_schedule
                else None,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "state": order.state,
                "main_invoice_reference": order.main_invoice.reference,
                "order_group_id": None,
                "organization": {
                    "id": str(order.organization.id),
                    "code": order.organization.code,
                    "title": order.organization.title,
                    "logo": "_this_field_is_mocked",
                    "address": {
                        "id": str(organization_address.id),
                        "address": organization_address.address,
                        "city": organization_address.city,
                        "country": organization_address.country,
                        "first_name": organization_address.first_name,
                        "is_main": organization_address.is_main,
                        "last_name": organization_address.last_name,
                        "postcode": organization_address.postcode,
                        "title": organization_address.title,
                    }
                    if organization_address
                    else None,
                    "enterprise_code": order.organization.enterprise_code,
                    "activity_category_code": order.organization.activity_category_code,
                    "contact_phone": order.organization.contact_phone,
                    "contact_email": order.organization.contact_email,
                    "dpo_email": order.organization.dpo_email,
                },
                "owner": owner.username,
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "product_id": str(product.id),
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "course_runs": [
                            {
                                "id": str(course_run.id),
                                "title": course_run.title,
                                "resource_link": course_run.resource_link,
                                "state": {
                                    "priority": course_run.state["priority"],
                                    "datetime": format_date(
                                        course_run.state["datetime"]
                                    ),
                                    "call_to_action": course_run.state[
                                        "call_to_action"
                                    ],
                                    "text": course_run.state["text"],
                                },
                                "start": format_date(course_run.start),
                                "end": format_date(course_run.end),
                                "enrollment_start": format_date(
                                    course_run.enrollment_start
                                ),
                                "enrollment_end": format_date(
                                    course_run.enrollment_end
                                ),
                                "languages": course_run.languages,
                            }
                            for course_run in target_course.course_runs.all().order_by(
                                "start"
                            )
                        ],
                        "position": target_course.order_relations.get(
                            order=order
                        ).position,
                        "is_graded": target_course.order_relations.get(
                            order=order
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in order.target_courses.all().order_by(
                        "order_relations__position"
                    )
                ],
            },
        )

    def test_api_order_read_detail_authenticated_not_owner(self):
        """Authenticated users should not be able to retrieve an order they don't own."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token("panoramix")

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertDictEqual(
            response.json(), {"detail": "No Order matches the given query."}
        )
