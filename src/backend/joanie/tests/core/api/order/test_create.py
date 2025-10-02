"""Tests for the Order create API."""

# pylint: disable=too-many-lines
import random
import uuid
from datetime import timedelta
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.utils import timezone

from viewflow import fsm

from joanie.core import enums, factories, models
from joanie.core.api import client as api_client
from joanie.core.models import CourseState
from joanie.core.serializers import fields
from joanie.core.utils import webhooks
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class OrderCreateApiTest(BaseAPITestCase):
    """Test the API of the Order create endpoint."""

    maxDiff = None

    def _get_fee_order_data(self, **kwargs):
        """Return a fee order linked to a course."""
        product = factories.ProductFactory(price=10.00)
        billing_address = BillingAddressDictFactory()
        return {
            **kwargs,
            "has_waived_withdrawal_right": True,
            "product_id": str(product.id),
            "course_code": product.courses.first().code,
            "billing_address": billing_address,
        }

    def _get_free_order_data(self, **kwargs):
        """Return a free order."""
        product = factories.ProductFactory(price=0.00)

        return {
            **kwargs,
            "has_waived_withdrawal_right": True,
            "product_id": str(product.id),
            "course_code": product.courses.first().code,
        }

    def _get_fee_enrollment_order_data(self, user, **kwargs):
        """Return a fee order linked to an enrollment."""
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE
        )
        enrollment = factories.EnrollmentFactory(
            user=user, course_run__course=offering.course
        )
        billing_address = BillingAddressDictFactory()

        return {
            **kwargs,
            "has_waived_withdrawal_right": True,
            "enrollment_id": str(enrollment.id),
            "product_id": str(offering.product.id),
            "billing_address": billing_address,
        }

    def test_api_order_create_anonymous(self):
        """Anonymous users should not be able to create an order."""
        product = factories.ProductFactory()
        data = {
            "has_waived_withdrawal_right": True,
            "course_code": product.courses.first().code,
            "product_id": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/", data=data, content_type="application/json"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            {"detail": "Authentication credentials were not provided."}, response.json()
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_api_order_create_authenticated_for_course_success(
        self, mock_sync, _mock_thumbnail
    ):
        """Any authenticated user should be able to create an order for a course."""
        archived_course_run = factories.CourseRunFactory(
            state=CourseState.ARCHIVED_CLOSED,
            is_listed=False,
        )
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        course = course_run.course
        course.course_runs.add(archived_course_run)

        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
            target_courses=[course],
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Certification",
                name="Become a certified learner certificate",
            ),
            price=100,
        )
        offering = product.offerings.first()
        factories.OfferingRuleFactory(
            course_product_relation=offering,
        )
        organization = offering.organizations.first()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
            "billing_address": BillingAddressDictFactory(),
        }
        token = self.get_user_token("panoramix")
        mock_sync.reset_mock()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        # sync has been called
        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            [
                {
                    "catalog_visibility": enums.COURSE_AND_SEARCH,
                    "certificate_discount": None,
                    "certificate_discounted_price": None,
                    "certificate_offer": enums.COURSE_OFFER_PAID,
                    "certificate_price": None,
                    "course": offering.course.code,
                    "discount": None,
                    "discounted_price": None,
                    "start": course_run.start.isoformat(),
                    "end": course_run.end.isoformat(),
                    "enrollment_start": course_run.enrollment_start.isoformat(),
                    "enrollment_end": course_run.enrollment_end.isoformat(),
                    "languages": course_run.languages,
                    "offer": enums.COURSE_OFFER_PAID,
                    "price": product.price,
                    "resource_link": f"https://example.com/api/v1.0/courses/{course.code}"
                    f"/products/{product.id}/",
                }
            ],
            synchronized_course_runs,
        )
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()
        organization_address = order.organization.addresses.filter(is_main=True).first()

        self.assertDictEqual(
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "payment_schedule": [],
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "credit_card_id": None,
                "enrollment": None,
                "main_invoice_reference": order.main_invoice.reference,
                "offering_rule_ids": [
                    str(offering_rule.id)
                    for offering_rule in order.offering_rules.all()
                ],
                "has_waived_withdrawal_right": True,
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
                "owner": "panoramix",
                "product_id": str(product.id),
                "state": order.state,
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "course_runs": [
                            {
                                "id": str(course_run.id),
                                "title": course_run.title,
                                "languages": course_run.languages,
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
                                "enrollment_start": (
                                    format_date(course_run.enrollment_start)
                                ),
                                "enrollment_end": format_date(
                                    course_run.enrollment_end
                                ),
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
            response.json(),
        )

        # user has been created
        self.assertEqual(models.User.objects.count(), 1)
        user = models.User.objects.get()
        self.assertEqual("panoramix", user.username)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_enrollment_success(
        self, _mock_thumbnail
    ):
        """Any authenticated user should be able to create an order for an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run__state=models.CourseState.ONGOING_OPEN,
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(
            price=0.00, type="certificate", courses=[enrollment.course_run.course]
        )
        organization = product.offerings.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        enrollment.refresh_from_db()
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(
            enrollment=enrollment,
            course__isnull=True,
            organization=organization,
            product=product,
        )
        organization_address = order.organization.addresses.filter(is_main=True).first()

        self.assertEqual(list(order.target_courses.all()), [])
        self.assertDictEqual(
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": None,
                "payment_schedule": [],
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "credit_card_id": None,
                "has_waived_withdrawal_right": True,
                "enrollment": {
                    "course_run": {
                        "course": {
                            "code": enrollment.course_run.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(enrollment.course_run.course.id),
                            "title": enrollment.course_run.course.title,
                        },
                        "end": format_date(enrollment.course_run.end),
                        "enrollment_end": (
                            format_date(enrollment.course_run.enrollment_end)
                        ),
                        "enrollment_start": (
                            format_date(enrollment.course_run.enrollment_start)
                        ),
                        "id": str(enrollment.course_run.id),
                        "languages": enrollment.course_run.languages,
                        "resource_link": enrollment.course_run.resource_link,
                        "start": format_date(enrollment.course_run.start),
                        "state": {
                            "call_to_action": enrollment.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": format_date(
                                enrollment.course_run.state.get("datetime")
                            ),
                            "priority": enrollment.course_run.state.get("priority"),
                            "text": enrollment.course_run.state.get("text"),
                        },
                        "title": enrollment.course_run.title,
                    },
                    "created_on": format_date(enrollment.created_on),
                    "id": str(enrollment.id),
                    "is_active": enrollment.is_active,
                    "state": enrollment.state,
                    "was_created_by_order": enrollment.was_created_by_order,
                },
                "main_invoice_reference": None,
                "offering_rule_ids": [],
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
                "owner": enrollment.user.username,
                "product_id": str(product.id),
                "state": enums.ORDER_STATE_COMPLETED,
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [],
            },
            response.json(),
        )

    def test_api_order_create_authenticated_for_enrollment_invalid(self):
        """The enrollment id passed in payload to create an order should exist."""
        enrollment = factories.EnrollmentFactory(
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(price=0.00, type="certificate")
        organization = product.offerings.first().organizations.first()

        data = {
            "enrollment_id": uuid.uuid4(),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {"enrollment_id": f"Enrollment with id {data['enrollment_id']} not found."},
            response.json(),
        )
        # no order has been created
        self.assertEqual(models.Order.objects.count(), 0)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_enrollment_not_owner(
        self, _mock_thumbnail
    ):
        """
        An authenticated user can not create an order for an enrollment s.he doesn't own.
        """
        enrollment = factories.EnrollmentFactory(
            course_run__state=models.CourseState.ONGOING_OPEN,
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(
            price=0.00, type="certificate", courses=[enrollment.course_run.course]
        )
        organization = product.offerings.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            {
                "enrollment": [
                    "The enrollment should belong to the owner of this order."
                ],
            },
            response.json(),
        )

    def test_api_order_create_submit_authenticated_organization_not_passed(self):
        """
        It should not be possible to create an order without passing an organization if there are
        none linked to the product.
        """
        target_course = factories.CourseFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[], target_courses=[target_course], price=0.00
        )
        factories.OfferingFactory(course=course, product=product, organizations=[])

        data = {
            "course_code": course.code,
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            [" 'Assign' transition conditions have not been met"],
            response.json(),
        )

    def test_api_order_create_authenticated_organization_not_passed_one(self):
        """
        It should be possible to create an order without passing
        an organization. If there is only one linked to the product, it should be assigned.
        """
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[target_course], price=0.00)
        organization = product.offerings.first().organizations.first()
        course = product.courses.first()

        data = {
            "course_code": course.code,
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        # order has been created
        self.assertEqual(
            models.Order.objects.filter(
                organization__isnull=True, course=course
            ).count(),
            0,
        )
        self.assertEqual(
            models.Order.objects.filter(
                organization=organization, course=course
            ).count(),
            1,
        )

    def test_api_order_create_authenticated_organization_passed_several(self):
        """
        It should be possible to create then submit an order without passing an
        organization if there are several linked to the product when it's free.
        The one with the least active order count should be allocated.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )
        offering = factories.OfferingFactory(
            product__price=0.00, organizations=[organization, expected_organization]
        )

        for state in enums.ORDER_STATES_BINDING:
            factories.OrderFactory(
                organization=organization,
                course=offering.course,
                product=offering.product,
                state=state,
            )

        ignored_states = [
            state
            for [state, _] in enums.ORDER_STATE_CHOICES
            if state not in enums.ORDER_STATES_BINDING
        ]
        for state in ignored_states:
            factories.OrderFactory(
                organization=expected_organization,
                course=offering.course,
                product=offering.product,
                state=state,
            )

        data = {
            "course_code": offering.course.code,
            "product_id": str(offering.product.id),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        order_id = response.json()["id"]
        # The chosen organization should be one of the organizations with the lowest order count
        organization_id = models.Order.objects.get(id=order_id).organization.id
        self.assertEqual(organization_id, expected_organization.id)

    def test_api_order_create_should_auto_assign_organization(self):
        """
        On create request, if the related order has no organization linked yet, the one
        implied in the course product organization with the least order should be
        assigned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        orders_data = [
            self._get_free_order_data(),
            self._get_fee_order_data(),
            self._get_fee_enrollment_order_data(user),
        ]

        for data in orders_data:
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            order_id = response.json()["id"]
            order = models.Order.objects.get(id=order_id)
            self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
            # Now order should have an organization set
            self.assertIsNotNone(order.organization)

    @mock.patch.object(api_client, "get_least_active_organization", return_value=None)
    def test_api_order_create_should_auto_assign_organization_if_needed(
        self, mocked_round_robin
    ):
        """
        Order should have organization auto assigned only on submit if it has
        not already one linked.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Auto assignment should have been triggered if order has no organization linked
        # order = factories.OrderFactory(owner=user, organization=None)
        # self.client.patch(
        #     f"/api/v1.0/orders/{order.id}/submit/",
        #     content_type="application/json",
        #     data={"billing_address": BillingAddressDictFactory()},
        #     HTTP_AUTHORIZATION=f"Bearer {token}",
        # )
        data = self._get_free_order_data()
        self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mocked_round_robin.assert_called_once()

        mocked_round_robin.reset_mock()

        # Auto assignment should not have been
        # triggered if order already has an organization linked
        # order = factories.OrderFactory(owner=user)
        # self.client.patch(
        #     f"/api/v1.0/orders/{order.id}/submit/",
        #     content_type="application/json",
        #     data={"billing_address": BillingAddressDictFactory()},
        #     HTTP_AUTHORIZATION=f"Bearer {token}",
        # )
        organization = models.Organization.objects.get()
        data.update(organization_id=str(organization.id))
        self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mocked_round_robin.assert_not_called()

    def test_api_order_create_auto_assign_organization_with_least_orders(self):
        """
        Order auto-assignment logic should always return the organization with the least
        active orders count for the given product course offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )

        offering = factories.OfferingFactory(
            organizations=[organization, expected_organization]
        )

        ignored_states = [
            state
            for [state, _] in enums.ORDER_STATE_CHOICES
            if state not in enums.ORDER_STATES_BINDING
        ]

        # Create orders for the first organization (1 for each ignored, 1 take in account)
        for state in ignored_states:
            factories.OrderFactory(
                organization=organization,
                product=offering.product,
                course=offering.course,
                state=state,
            )
        factories.OrderFactory(
            organization=organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_PENDING,
        )

        # ignored orders for the second organization
        for state in ignored_states:
            factories.OrderFactory(
                organization=expected_organization,
                product=offering.product,
                course=offering.course,
                state=state,
            )

        # Then create an order without organization
        data = {
            "course_code": offering.course.code,
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(expected_organization, order.organization)

    def test_api_order_create_organization_with_least_orders_is_consistent(self):
        """
        Ensure that the organization auto assignation is consistent no matter
        if organizations are implied in other offerings. In some case, it
        appears that the organization with the least orders count is not the one assigned.
        This test aims to reproduce the issue and ensure it is fixed.

        We set up a test case with 2 organizations. The organizations[0] should be the one
        with the least orders, but by creating several other offerings where
        the organizations are implied and are sometimes authors, we get the wrong behavior.

        Useful resource : https://stackoverflow.com/a/69969582
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        organizations = factories.OrganizationFactory.create_batch(2)

        # Create noisy data to reproduce the issue
        # We create more offerings with organizations[0] as author
        for r in factories.OfferingFactory.create_batch(3, organizations=organizations):
            r.course.organizations.add(organizations[0])
            factories.OrderFactory.create(
                product=r.product,
                course=r.course,
                organization=organizations[0],
                state=enums.ORDER_STATE_COMPLETED,
            )
            factories.OrderFactory.create(
                product=r.product,
                course=r.course,
                organization=organizations[1],
                state=enums.ORDER_STATE_COMPLETED,
            )
        for r in factories.OfferingFactory.create_batch(1, organizations=organizations):
            r.course.organizations.add(organizations[1])
            factories.OrderFactory.create(
                product=r.product,
                course=r.course,
                organization=organizations[0],
                state=enums.ORDER_STATE_COMPLETED,
            )
            factories.OrderFactory.create(
                product=r.product,
                course=r.course,
                organization=organizations[1],
                state=enums.ORDER_STATE_COMPLETED,
            )

        # Now we create an offering
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=organizations
        )
        # Then create 1 active order for the organizations[0]
        factories.OrderFactory.create(
            product=product,
            course=course,
            organization=organizations[0],
            state=enums.ORDER_STATE_COMPLETED,
        )
        # And 2 active orders for the organizations[1]
        factories.OrderFactory.create_batch(
            2,
            product=product,
            course=course,
            organization=organizations[1],
            state=enums.ORDER_STATE_COMPLETED,
        )

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Then create an order without organization
        # It should be assigned to the organizations[0] as it has the least active orders
        data = {
            "course_code": offering.course.code,
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(organizations[0], order.organization)
        self.assertEqual(organizations[0].order_set.count(), 6)
        self.assertEqual(organizations[1].order_set.count(), 6)

    def test_api_order_create_get_organization_with_least_active_orders_prefer_author(
        self,
    ):
        """
        In case of order count equality, the method _get_organization_with_least_orders should
        return first organization which is also an author of the course.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )

        offering = factories.OfferingFactory(
            organizations=[organization, expected_organization]
        )

        offering.course.organizations.set([expected_organization])

        # Create 3 orders for the first organization (1 draft, 1 pending, 1 canceled)
        factories.OrderFactory(
            organization=organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_PENDING,
        )
        factories.OrderFactory(
            organization=organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # 3 ignored orders for the second organization (1 draft, 1 assigned, 1 canceled)
        factories.OrderFactory(
            organization=expected_organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_DRAFT,
        )
        factories.OrderFactory(
            organization=expected_organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_ASSIGNED,
        )
        factories.OrderFactory(
            organization=expected_organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # Then create an order without organization
        data = {
            "course_code": offering.course.code,
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(expected_organization, order.organization)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_has_read_only_fields(self, _mock_thumbnail):
        """
        If an authenticated user tries to create an order with more fields than "product" and
        "course" or "enrollment", they should not be taken into account as they are set by
        the server.
        """
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses, price=0.00)
        course = product.courses.first()
        organization = product.offerings.first().organizations.first()
        self.assertCountEqual(
            list(product.target_courses.order_by("offerings")), target_courses
        )

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "id": uuid.uuid4(),
            "amount": 0.00,
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order = models.Order.objects.get()
        # - Order has been successfully created and read_only_fields
        #   has been ignored.
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(models.Order.objects.count(), 1)
        self.assertCountEqual(
            list(order.target_courses.order_by("offerings")), target_courses
        )

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        organization_address = order.organization.addresses.filter(is_main=True).first()
        # - id, price and state has not been set according to data values
        self.assertDictEqual(
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "payment_schedule": [],
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "credit_card_id": None,
                "enrollment": None,
                "main_invoice_reference": None,
                "offering_rule_ids": [],
                "has_waived_withdrawal_right": True,
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
                "owner": "panoramix",
                "product_id": str(product.id),
                "target_enrollments": [],
                "state": enums.ORDER_STATE_COMPLETED,
                "target_courses": [
                    {
                        "code": target_course.code,
                        "course_runs": [
                            {
                                "id": course_run.id,
                                "course": {
                                    "code": str(course_run.course.code),
                                    "title": str(course_run.course.title),
                                },
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
                                "enrollment_start": (
                                    format_date(course_run.enrollment_start)
                                ),
                                "enrollment_end": format_date(
                                    course_run.enrollment_end
                                ),
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
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
            },
            response.json(),
        )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(title="balançoire", price=0.00)
        offering = factories.OfferingFactory(
            product=product, organizations=[organization]
        )
        course = factories.CourseFactory(title="mathématiques")
        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            {
                "__all__": [
                    'This order cannot be linked to the product "balançoire", '
                    'the course "mathématiques".'
                ]
            },
            response.json(),
        )

        # Linking the course to the product should solve the problem
        offering.course = course
        offering.save()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertTrue(models.Order.objects.filter(course=course).exists())

    def test_api_order_create_authenticated_invalid_organization(self):
        """
        The organization passed in payload to create an order should be one of the
        product's organizations.
        """
        course = factories.CourseFactory(title="mathématiques")
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(
            courses=[course], title="balançoire", price=0.00
        )
        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        token = self.get_user_token("panoramix")

        # Linking the organization to the product should solve the problem
        product.offerings.first().organizations.add(organization)
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertTrue(models.Order.objects.filter(organization=organization).exists())

    def test_api_order_create_authenticated_missing_product_then_course(self):
        """
        The payload must contain at least a product uid, withdrawal right and a course code.
        """
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "has_waived_withdrawal_right": ["This field is required."],
                "product_id": ["This field is required."],
            },
        )

        product = factories.ProductFactory()
        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "has_waived_withdrawal_right": True,
                "product_id": str(product.id),
            },
        )

        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            {"__all__": ["Either the course or the enrollment field is required."]},
            response.json(),
        )

    def test_api_order_create_authenticated_product_course_unicity(self):
        """
        If a user tries to create a new order while he has already a not canceled order
        for the couple product - course, a bad request response should be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=0.00)
        organization = product.offerings.first().organizations.first()

        # User already owns an order for this product and course
        order = factories.OrderFactory(owner=user, course=course, product=product)

        data = {
            "product_id": str(product.id),
            "course_code": course.code,
            "organization_id": str(organization.id),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {"__all__": ["An order for this product and course already exists."]},
            response.json(),
        )

        # But if we cancel the first order, user should be able to create a new order
        order.flow.cancel()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

    def test_api_order_create_authenticated_billing_address_required(self):
        """
        When creating an order related to a fee product, if no billing address is
        given, the order is not created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=200.0)
        organization = product.offerings.first().organizations.first()

        data = {
            "product_id": str(product.id),
            "course_code": course.code,
            "organization_id": str(organization.id),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_payment_binding(self, _mock_thumbnail):
        """
        Create an order to a fee product and then submitting it should create a
        payment and bind payment information into the response.
        :
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.offerings.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }

        with self.record_performance():
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(models.Order.objects.count(), 1)

        order = models.Order.objects.get(product=product, course=course, owner=user)
        organization_address = order.organization.addresses.filter(is_main=True).first()

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertDictEqual(
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "payment_schedule": [],
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "credit_card_id": None,
                "enrollment": None,
                "main_invoice_reference": order.main_invoice.reference,
                "offering_rule_ids": [],
                "has_waived_withdrawal_right": True,
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
                "owner": user.username,
                "product_id": str(product.id),
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "state": enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organization_id": {
                            "code": target_course.organization.code,
                            "title": target_course.organization.title,
                        },
                        "course_runs": [
                            {
                                "id": course_run.id,
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
                                "enrollment_start": (
                                    format_date(course_run.enrollment_start)
                                ),
                                "enrollment_end": format_date(
                                    course_run.enrollment_end
                                ),
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
            response.json(),
        )

    def test_api_order_create_authenticated_nb_seats(self):
        """
        The number of completed/pending orders on a product should not be above the limit
        set by the number of seats
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = models.OfferingRule.objects.create(
            course_product_relation=offering, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            state=enums.ORDER_STATE_COMPLETED,
            offering_rules=[offering_rule],
        )
        data = {
            "course_code": course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {
                "offering_rule": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
            response.json(),
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_nb_seats_discount(self, _mock_thumbnail):
        """
        When a discount rule with seats limit is reached, we should be able
        to create a new order on the same product.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = models.OfferingRule.objects.create(
            course_product_relation=offering,
            nb_seats=1,
            discount=factories.DiscountFactory(),
        )
        billing_address = BillingAddressDictFactory()
        existing_order = factories.OrderFactory(
            product=product,
            course=course,
            state=enums.ORDER_STATE_COMPLETED,
            offering_rules=[offering_rule],
        )
        data = {
            "course_code": course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 2
        )
        order = models.Order.objects.exclude(id=existing_order.id).first()
        organization_address = order.organization.addresses.filter(is_main=True).first()

        self.assertDictEqual(
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "payment_schedule": [],
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "credit_card_id": None,
                "enrollment": None,
                "main_invoice_reference": order.main_invoice.reference,
                "offering_rule_ids": [],
                "has_waived_withdrawal_right": True,
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
                "owner": user.username,
                "product_id": str(product.id),
                "state": enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "course_runs": [
                            {
                                "id": course_run.id,
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
                                "enrollment_start": (
                                    format_date(course_run.enrollment_start)
                                ),
                                "enrollment_end": format_date(
                                    course_run.enrollment_end
                                ),
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
            response.json(),
        )

    def test_api_order_create_authenticated_no_seats(self):
        """
        If the number of seats is set to 0 on an active offering rule, we should not be able
        to create a new order on this group.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OfferingRule.objects.create(
            course_product_relation=offering, is_active=True, nb_seats=0
        )
        billing_address = BillingAddressDictFactory()
        data = {
            "course_code": course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {
                "offering_rule": [
                    f"Maximum number of orders reached for product {offering.product.title}"
                ]
            },
            response.json(),
        )
        self.assertEqual(
            models.Order.objects.filter(product=product, course=course).count(), 0
        )

    def test_api_order_create_authenticated_nb_seat_is_none_on_active_offering_rule(
        self,
    ):
        """
        If `nb_seats` is set to `None` on an active offering rule, there should be no limit
        to the number of orders.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        offering = factories.OfferingFactory(
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering, nb_seats=None, is_active=True
        )
        factories.OrderFactory.create_batch(
            10,
            product=offering.product,
            course=offering.course,
            offering_rules=[offering_rule],
        )
        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(
                product=offering.product, course=offering.course
            ).count(),
            11,
        )

    def test_api_order_create_authenticated_free_product_no_billing_address(self):
        """
        Create an order on a free product without billing address
        should create an order then transition its state to 'validated'.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=0.00)
        organization = product.offerings.first().organizations.first()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "has_waived_withdrawal_right": True,
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_COMPLETED)

    def test_api_order_create_authenticated_to_pending(self):
        """
        Create an order on a fee product with billing address and credit card.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        product = factories.ProductFactory(
            courses=[course], target_courses=[run.course]
        )
        organization = product.offerings.first().organizations.first()
        billing_address = BillingAddressDictFactory()
        credit_card = CreditCardFactory(owners=[user])

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "credit_card_id": str(credit_card.id),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_PENDING)
        order_id = response.json()["id"]
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    def test_api_order_create_offering_rule_unrelated(self):
        """The offering rule must apply to the product being ordered."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(
            organizations=[organization],
        )
        billing_address = BillingAddressDictFactory()

        # Offering rule related to another product
        factories.OfferingRuleFactory()

        data = {
            "course_code": offering.course.code,
            "organization_id": str(organization.id),
            "product_id": str(offering.product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(
                course=offering.course, product=offering.product
            ).count(),
            1,
        )

    def test_api_order_create_several_offering_rules(self):
        """A product can have several active offering rules."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule1 = models.OfferingRule.objects.create(
            course_product_relation=offering, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            offering_rules=[offering_rule1],
            state=random.choice(
                [enums.ORDER_STATE_PENDING, enums.ORDER_STATE_COMPLETED]
            ),
        )
        data = {
            "course_code": course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(user)

        # Offering rule 1 should already be full
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {
                "offering_rule": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
            response.json(),
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

        offering_rule2 = models.OfferingRule.objects.create(
            course_product_relation=offering, nb_seats=1
        )
        # Offering rule 2 should be assigned
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 2
        )
        self.assertEqual(
            models.Order.objects.filter(offering_rules=offering_rule2.id).count(), 1
        )

    def test_api_order_create_inactive_offering_rules(self):
        """An inactive offering rule should not be taken into account."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OfferingRule.objects.create(
            course_product_relation=offering, nb_seats=1, is_active=False
        )
        billing_address = BillingAddressDictFactory()
        data = {
            "course_code": course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": True,
        }
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

    @mock.patch("joanie.core.models.CourseProductRelation.is_withdrawable")
    def test_api_order_create_for_product_without_withdrawal_period(
        self, mock_is_withdrawable
    ):
        """
        If a product has no withdrawal period, the order should failed until the user
        has waived to its withdrawal right.
        """
        mock_is_withdrawable.__get__ = mock.Mock(return_value=False)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        billing_address = BillingAddressDictFactory()

        data = {
            "course_code": offering.course.code,
            "product_id": str(offering.product.id),
            "billing_address": billing_address,
            "has_waived_withdrawal_right": False,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            {"has_waived_withdrawal_right": "This field must be set to True."},
            response.json(),
        )

        data.update({"has_waived_withdrawal_right": True})
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

    def test_api_order_create_authenticated_product_course_unicity_when_not_in_inactive_state(
        self,
    ):
        """
        Allow authenticated user to create a new order when a triplet product-course-owner
        of a previous order already exists and the state of that one is in an inactive
        state (`cancelled`, `refunded`, or `refunding`). Otherwise, it should not let him create
        a new order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                course = factories.CourseFactory()
                product = factories.ProductFactory(courses=[course], price=10.00)
                organization = product.offerings.first().organizations.first()
                billing_address = BillingAddressDictFactory()
                factories.OrderGeneratorFactory(
                    owner=user,
                    course=course,
                    product=product,
                    organization=organization,
                    state=state,
                )

                data = {
                    "product_id": str(product.id),
                    "course_code": course.code,
                    "organization_id": str(organization.id),
                    "billing_address": billing_address,
                    "has_waived_withdrawal_right": True,
                }

                response = self.client.post(
                    "/api/v1.0/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                if state in enums.ORDER_INACTIVE_STATES:
                    self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
                else:
                    self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
                    self.assertEqual(
                        {
                            "__all__": [
                                "An order for this product and course already exists."
                            ]
                        },
                        response.json(),
                    )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_api_order_create_authenticated_product_enrollment_unicity_when_not_in_inactive_state(
        self,
        mock_sync,
    ):
        """
        Allow authenticated user to create a new order when a triplet product-enrollment-owner
        of a previous order already exists and the state of that one is in an inactive
        state (`cancelled`, `refunded`, or `refunding`). Otherwise, it should not let him create
        a new order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                enrollment = factories.EnrollmentFactory(
                    user=user, course_run__state=CourseState.ONGOING_OPEN
                )
                course = enrollment.course_run.course
                course_run = course.course_runs.first()
                product = factories.ProductFactory(
                    courses=[enrollment.course_run.course],
                    price=10.00,
                    type=enums.PRODUCT_TYPE_CERTIFICATE,
                )
                offering = product.offerings.first()
                organization = offering.organizations.first()
                billing_address = BillingAddressDictFactory()

                factories.OrderFactory(
                    owner=user,
                    course=None,
                    enrollment=enrollment,
                    product=product,
                    organization=organization,
                    state=state,
                )
                mock_sync.reset_mock()

                data = {
                    "enrollment_id": str(enrollment.id),
                    "organization_id": str(organization.id),
                    "product_id": str(product.id),
                    "has_waived_withdrawal_right": True,
                    "billing_address": billing_address,
                }

                response = self.client.post(
                    "/api/v1.0/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                if state in enums.ORDER_INACTIVE_STATES:
                    self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
                    # sync has been called
                    self.assertEqual(mock_sync.call_count, 1)
                    synchronized_course_run = mock_sync.call_args_list[0][0][0][0]
                    self.assertEqual(
                        {
                            "catalog_visibility": enums.COURSE_AND_SEARCH,
                            "certificate_discount": None,
                            "certificate_discounted_price": None,
                            "certificate_offer": enums.COURSE_OFFER_PAID,
                            "certificate_price": product.price,
                            "course": offering.course.code,
                            "discount": None,
                            "discounted_price": None,
                            "start": synchronized_course_run["start"],
                            "end": synchronized_course_run["end"],
                            "enrollment_start": synchronized_course_run[
                                "enrollment_start"
                            ],
                            "enrollment_end": synchronized_course_run["enrollment_end"],
                            "languages": course_run.languages,
                            "offer": enums.COURSE_OFFER_FREE,
                            "price": None,
                            "resource_link": synchronized_course_run["resource_link"],
                        },
                        synchronized_course_run,
                    )
                else:
                    self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
                    self.assertEqual(
                        {
                            "__all__": [
                                "An order for this product and enrollment already exists."
                            ]
                        },
                        response.json(),
                    )

    def test_api_order_create_when_offering_rule_is_active_and_nb_seats_is_none(self):
        """
        When create an order and the offering rule is active and has a number of seat
        set to None, it should let us create unlimited number of orders. Although,
        when the offering rule is not active, it should not create the order on the offering rule.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=None,
        )
        factories.OrderFactory.create_batch(
            2,
            course=offering.course,
            product=offering.product,
            offering_rules=[offering_rule],
            state=enums.ORDER_STATE_PENDING,
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(offering_rules=offering_rule.id).count(), 3
        )

    def test_api_order_create_when_offering_rule_is_not_active_and_nb_seats_is_0(self):
        """
        When we want to create an order and the offering rule is not active and
        has a number of seat to 0, the offering rule should be ignored,
        and the order should be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        offering = factories.OfferingFactory()
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=False,
            nb_seats=0,
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(response.json()["offering_rule_ids"], [])

    def test_api_order_create_when_offering_rule_is_active_but_not_enabled_yet(self):
        """
        When an authenticated user passes in the payload an offering rule that is not yet enabled
        to create his order, the order should not be created. When the user passes an order
        group that is enabled, the order is created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        offering = factories.OfferingFactory()
        # This offering rule will be enabled tomorrow
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            start=timezone.now() + timedelta(days=1),
        )
        # This offering rule has expired in time
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=False,
            end=timezone.now() - timedelta(days=1),
        )
        # This offering rule is active and enabled
        offering_rule_enabled = factories.OfferingRuleFactory(
            course_product_relation=offering, is_active=True, start=timezone.now()
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(
            response.json()["offering_rule_ids"], [str(offering_rule_enabled.id)]
        )

    def test_api_order_create_discount_rate_on_offering_rule(self):
        """
        Authenticated user wants to create an order on the offering rule that is enabled and
        has a discount rate. The created order should have the total value of the discounted price.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        cases_inside_date_range = [
            {
                "start": timezone.now() - timedelta(seconds=10),
                "end": None,
            },
            {
                "start": None,
                "end": timezone.now() + timedelta(seconds=10),
            },
            {
                "start": timezone.now() - timedelta(seconds=10),
                "end": timezone.now() + timedelta(seconds=10),
            },
        ]
        for case in cases_inside_date_range:
            with self.subTest(start=case["start"], end=case["end"]):
                offering = factories.OfferingFactory(product__price=100)
                offering_rule = factories.OfferingRuleFactory(
                    discount=factories.DiscountFactory(rate=0.1),
                    course_product_relation=offering,
                    is_active=True,
                    start=case["start"],
                    end=case["end"],
                )

                data = {
                    "course_code": offering.course.code,
                    "organization_id": str(offering.organizations.first().id),
                    "product_id": str(offering.product.id),
                    "billing_address": BillingAddressDictFactory(),
                    "has_waived_withdrawal_right": True,
                }

                response = self.client.post(
                    "/api/v1.0/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

                order = models.Order.objects.get(offering_rules=offering_rule.id)
                self.assertEqual(order.total, 90)

    def test_api_order_create_discount_rate_on_offering_rule_not_enabled(self):
        """
        Authenticated user wants to create an order on the offering rule that is not enabled and
        has a discount rate. The created order should not be discounted.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        cases_outside_date_range = [
            {
                "start": timezone.now() + timedelta(seconds=10),
                "end": None,
            },
            {
                "start": None,
                "end": timezone.now() - timedelta(seconds=10),
            },
            {
                "start": timezone.now() + timedelta(seconds=10),
                "end": timezone.now() + timedelta(seconds=10),
            },
        ]
        for case in cases_outside_date_range:
            with self.subTest(start=case["start"], end=case["end"]):
                offering = factories.OfferingFactory(product__price=100)
                factories.OfferingRuleFactory(
                    discount=factories.DiscountFactory(rate=0.1),
                    course_product_relation=offering,
                    is_active=True,
                    start=case["start"],
                    end=case["end"],
                )

                data = {
                    "course_code": offering.course.code,
                    "organization_id": str(offering.organizations.first().id),
                    "product_id": str(offering.product.id),
                    "billing_address": BillingAddressDictFactory(),
                    "has_waived_withdrawal_right": True,
                }

                response = self.client.post(
                    "/api/v1.0/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
                order = models.Order.objects.get(id=response.json()["id"])
                self.assertEqual(order.total, 100)

    def test_api_order_create_discount_amount_on_offering_rule(self):
        """
        Authenticated user wants to create an order on the offering rule that is enabled and
        has a discount amount. The created order should have the total value of the discounted
        price.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        cases_inside_date_range = [
            {
                "start": timezone.now() - timedelta(seconds=10),
                "end": None,
            },
            {
                "start": None,
                "end": timezone.now() + timedelta(seconds=10),
            },
            {
                "start": timezone.now() - timedelta(seconds=10),
                "end": timezone.now() + timedelta(seconds=10),
            },
        ]
        for case in cases_inside_date_range:
            with self.subTest(start=case["start"], end=case["end"]):
                offering = factories.OfferingFactory(product__price=100)
                offering_rule = factories.OfferingRuleFactory(
                    discount=factories.DiscountFactory(amount=20),
                    course_product_relation=offering,
                    is_active=True,
                    start=case["start"],
                    end=case["end"],
                )

                data = {
                    "course_code": offering.course.code,
                    "organization_id": str(offering.organizations.first().id),
                    "offering_rule_id": str(offering_rule.id),
                    "product_id": str(offering.product.id),
                    "billing_address": BillingAddressDictFactory(),
                    "has_waived_withdrawal_right": True,
                }

                response = self.client.post(
                    "/api/v1.0/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                order = models.Order.objects.get(offering_rules=offering_rule.id)

                self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
                self.assertEqual(order.total, 80)

    def test_api_order_create_discount_rate_offering_rule_enabled_no_more_seat_available(
        self,
    ):
        """
        Authenticated user creates an order on an offering rule that is enabled but has no more
        seat available, the order should not be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=1,
        )
        factories.OrderFactory(
            offering_rules=[offering_rule],
            course=offering.course,
            product=offering.product,
            state=random.choice(
                [enums.ORDER_STATE_COMPLETED, enums.ORDER_STATE_PENDING]
            ),
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "offering_rule_id": str(offering_rule.id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            {
                "offering_rule": [
                    f"Maximum number of orders reached for product {offering.product.title}"
                ]
            },
            response.json(),
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_api_order_create_discount_rate_offering_rule_enabled_last_seat_available(
        self,
        mock_sync,
    ):
        """
        Authenticated user creates an order on an offering rule that is enabled and has one
        seat available, the order should be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
        )
        offering = factories.OfferingFactory(course__course_runs=[course_run])
        product = offering.product
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=2,
        )
        factories.OrderFactory(
            offering_rules=[offering_rule],
            course=offering.course,
            product=offering.product,
            state=random.choice(
                [enums.ORDER_STATE_COMPLETED, enums.ORDER_STATE_PENDING]
            ),
        )
        mock_sync.reset_mock()

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "offering_rule_id": str(offering_rule.id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        # sync has been called
        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0][0]
        self.assertEqual(
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": None,
                "certificate_price": None,
                "course": offering.course.code,
                "discount": None,
                "discounted_price": None,
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{offering.course.code}/products/{product.id}/",
            },
            synchronized_course_runs,
        )

    def test_api_order_create_discount_voucher(self):
        """
        An order created with a voucher should have the total value of the discounted price.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.1),
            multiple_use=False,
            multiple_users=False,
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
            "voucher_code": voucher.code,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        order = models.Order.objects.get()
        self.assertEqual(order.total, 90)
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

    def test_api_order_create_discount_voucher_unusable(self):
        """
        An order creation with a voucher that is already consumed should fail.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.1),
            multiple_use=False,
            multiple_users=False,
        )
        factories.OrderFactory(
            course=offering.course,
            product=offering.product,
            voucher=voucher,
        )

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
            "voucher_code": voucher.code,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_order_create_voucher_full_discount_rate_for_credential_product_type(
        self,
    ):
        """
        When an authenticated user uses a full discount voucher with the rate of 1 to make an
        order on a credential product, the created order's total should be at 0, the state should
        be 'completed' and a main invoice should be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        voucher = factories.VoucherFactory(discount__rate=1)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=self._get_fee_order_data(voucher_code=voucher.code),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        order = models.Order.objects.get()
        self.assertEqual(order.total, 0)
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)
        self.assertIsNotNone(order.main_invoice)

    def test_api_order_create_voucher_full_discount_rate_for_enrollment_certificate_product_type(
        self,
    ):
        """
        When an authenticated user uses a full discount voucher with the rate of 1 to make an
        order on a certificate product, the created order's total should be at 0, the state should
        be 'completed' and a main invoice should be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        voucher = factories.VoucherFactory(discount__rate=1)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=self._get_fee_enrollment_order_data(user, voucher_code=voucher.code),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        order = models.Order.objects.get()
        self.assertEqual(order.total, 0)
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)
        self.assertIsNotNone(order.main_invoice)

    @mock.patch("joanie.core.models.products.Order.enroll_user_to_course_run")
    def test_api_order_create_with_voucher_code_from_batch_order_already_used(
        self, mock_enroll_user_to_course_run
    ):
        """
        When the voucher code from a batch order has already been used by the user, he cannot
        use that same voucher code twice.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            nb_seats=2, state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        batch_order.generate_orders()
        voucher_codes = batch_order.vouchers

        order = batch_order.orders.get(voucher__code=voucher_codes[0])
        order.owner = user
        order.flow.update()
        order.save()
        # Make sure he is enrolled to the course run
        mock_enroll_user_to_course_run.assert_called_once()
        mock_enroll_user_to_course_run.reset_mock()
        # Prepare the data where he attempts to use his voucher code a second time
        data = {
            "organization_id": batch_order.organization.id,
            "product_id": batch_order.offering.product.id,
            "course_code": batch_order.offering.course.code,
            "voucher_code": voucher_codes[0],
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # Make sure the transition did not succeed and enroll method was not called
        mock_enroll_user_to_course_run.assert_not_called()

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    @mock.patch("joanie.core.models.products.Order.enroll_user_to_course_run")
    def test_api_order_create_with_voucher_code_from_batch_order_used_by_another_user(
        self, mock_enroll_user_to_course_run
    ):
        """
        When the voucher code from a batch order has been used by another user, the
        order should not be assigned. Otherwise, he should use another code to be assigned to
        an existing order with the state to own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            nb_seats=2, state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        batch_order.generate_orders()
        voucher_codes = batch_order.vouchers

        # Let's assign the first order with the 1st voucher code with an owner
        order = batch_order.orders.get(voucher__code=voucher_codes[0])
        order.owner = factories.UserFactory()
        order.flow.update()
        order.save()
        # Make sure that flow update enrolls the owner to the course run
        mock_enroll_user_to_course_run.assert_called_once()
        mock_enroll_user_to_course_run.reset_mock()
        # Let's now simulate that the second owner uses the wrong voucher code to claim an order
        data = {
            "organization_id": batch_order.organization.id,
            "product_id": batch_order.offering.product.id,
            "course_code": batch_order.offering.course.code,
            "voucher_code": voucher_codes[0],
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # He should not be enrolled because he used the wrong voucher code that was consumed
        mock_enroll_user_to_course_run.assert_not_called()

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        # We will use the second available voucher code from the batch order
        data.update(voucher_code=voucher_codes[1])

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # Make sure he is enrolled to the course run
        mock_enroll_user_to_course_run.assert_called_once()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        order = models.Order.objects.get(owner=user)
        # The order should be marked as `completed`
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    @mock.patch(
        "joanie.core.flows.order.OrderFlow.complete",
        side_effect=fsm.TransitionNotAllowed,
    )
    @mock.patch("joanie.core.models.products.Order.enroll_user_to_course_run")
    def test_api_order_create_with_voucher_code_transition_to_complete_state_fails(
        self, mock_enroll_user_to_course_run, _mock_can_be_state_complete
    ):
        """
        When an error occurs during the transition of the order to completed, the order should
        not be claimed and still available and the voucher code should still be usable by the
        user. The user should not be enrolled to course run.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            nb_seats=2,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        batch_order.generate_orders()
        voucher_codes = batch_order.vouchers
        order = batch_order.orders.get(voucher__code=voucher_codes[0])

        data = {
            "organization_id": batch_order.organization.id,
            "product_id": batch_order.offering.product.id,
            "course_code": batch_order.offering.course.code,
            "voucher_code": voucher_codes[0],
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mock_enroll_user_to_course_run.assert_not_called()

        voucher = models.Voucher.objects.get(code=voucher_codes[0])

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
        self.assertTrue(voucher.is_usable_by(user.id))

    def test_api_order_create_with_fake_voucher_code(self):
        """
        Authenticated user attempts to pass a fake voucher code to claim an order.
        He should get an error in return.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            offering__product__price=100,
            nb_seats=2,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        data = {
            "organization_id": batch_order.organization.id,
            "product_id": batch_order.offering.product.id,
            "course_code": batch_order.offering.course.code,
            "voucher_code": "fake_voucher_code",
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    @mock.patch("joanie.core.models.products.Order.enroll_user_to_course_run")
    def test_api_order_create_with_voucher_code_from_a_batch_order(
        self, mock_enroll_user_to_course_run
    ):
        """
        When the user uses a voucher code that was generated through a batch order,
        he should be assigned to one of the orders available. When it succeeds, the
        method `enroll_user_to_course_run` should be called in the order flow state transition.
        Finally, the voucher code should not be usable anymore by the user once used.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            offering__product__price=100,
            nb_seats=2,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        batch_order.generate_orders()
        voucher_codes = batch_order.vouchers

        data = {
            "organization_id": batch_order.organization.id,
            "product_id": batch_order.offering.product.id,
            "course_code": batch_order.offering.course.code,
            "voucher_code": voucher_codes[0],
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mock_enroll_user_to_course_run.assert_called_once()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        order = models.Order.objects.get(owner=user)
        voucher = models.Voucher.objects.get(code=voucher_codes[0])

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)
        self.assertFalse(voucher.is_usable_by(user.id))
