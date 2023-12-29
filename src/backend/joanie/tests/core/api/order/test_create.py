"""Tests for the Order create API."""
# pylint: disable=too-many-lines
import random
import uuid
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test.client import RequestFactory

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.exceptions import CreatePaymentFailed
from joanie.payment.factories import (
    BillingAddressDictFactory,
    CreditCardFactory,
    InvoiceFactory,
)
from joanie.tests.base import BaseAPITestCase


class OrderCreateApiTest(BaseAPITestCase):
    """Test the API of the Order create endpoint."""

    maxDiff = None

    def test_api_order_create_anonymous(self):
        """Anonymous users should not be able to create an order."""
        product = factories.ProductFactory()
        data = {
            "course_code": product.courses.first().code,
            "product_id": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_course_success(self, _mock_thumbnail):
        """Any authenticated user should be able to create an order for a course."""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses, price=0.00)
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()

        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": "panoramix",
                "product_id": str(product.id),
                "state": "draft",
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
                                    "datetime": course_run.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                    "call_to_action": course_run.state[
                                        "call_to_action"
                                    ],
                                    "text": course_run.state["text"],
                                },
                                "start": course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "end": course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
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
        )

        with self.assertNumQueries(28):
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # user has been created
        self.assertEqual(models.User.objects.count(), 1)
        user = models.User.objects.get()
        self.assertEqual(user.username, "panoramix")
        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        self.assertDictEqual(response.json(), {"payment_info": None})

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
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(
            enrollment=enrollment,
            course__isnull=True,
            organization=organization,
            product=product,
        )

        self.assertEqual(list(order.target_courses.all()), [])
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": None,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": {
                    "course_run": {
                        "course": {
                            "code": enrollment.course_run.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(enrollment.course_run.course.id),
                            "title": enrollment.course_run.course.title,
                        },
                        "end": enrollment.course_run.end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "enrollment_end": (
                            enrollment.course_run.enrollment_end.isoformat().replace(
                                "+00:00", "Z"
                            )
                        ),
                        "enrollment_start": (
                            enrollment.course_run.enrollment_start.isoformat().replace(
                                "+00:00", "Z"
                            )
                        ),
                        "id": str(enrollment.course_run.id),
                        "languages": enrollment.course_run.languages,
                        "resource_link": enrollment.course_run.resource_link,
                        "start": enrollment.course_run.start.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "state": {
                            "call_to_action": enrollment.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": enrollment.course_run.state.get("datetime")
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "priority": enrollment.course_run.state.get("priority"),
                            "text": enrollment.course_run.state.get("text"),
                        },
                        "title": enrollment.course_run.title,
                    },
                    "created_on": enrollment.created_on.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "id": str(enrollment.id),
                    "is_active": enrollment.is_active,
                    "state": enrollment.state,
                    "was_created_by_order": enrollment.was_created_by_order,
                },
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": enrollment.user.username,
                "product_id": str(product.id),
                "state": "draft",
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [],
            },
        )

    def test_api_order_create_authenticated_for_enrollment_invalid(self):
        """The enrollment id passed in payload to create an order should exist."""
        enrollment = factories.EnrollmentFactory(
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(price=0.00, type="certificate")
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": uuid.uuid4(),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"enrollment_id": f"Enrollment with id {data['enrollment_id']} not found."},
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
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "enrollment": [
                    "The enrollment should belong to the owner of this order."
                ],
            },
        )

    def test_api_order_create_submit_authenticated_organization_not_passed(self):
        """
        It should be possible to create an order without passing an organization if there are
        none linked to the product, but be impossible to submit
        """
        target_course = factories.CourseFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[], target_courses=[target_course], price=0.00
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[]
        )

        data = {
            "course_code": course.code,
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        order_id = response.json()["id"]
        self.assertTrue(models.Order.objects.filter(id=order_id).exists())
        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            models.Order.objects.get(id=order_id).state, enums.ORDER_STATE_DRAFT
        )
        self.assertDictEqual(
            response.json(),
            {
                "__all__": ["Order should have an organization if not in draft state"],
            },
        )

    def test_api_order_create_authenticated_organization_not_passed_one(self):
        """
        It should be possible to create then submit an order without passing
        an organization if there is only one linked to the product.
        """
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[target_course], price=0.00)
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()

        data = {
            "course_code": course.code,
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        # order has been created

        self.assertEqual(
            models.Order.objects.filter(
                organization__isnull=True, course=course
            ).count(),
            1,
        )

        response = self.client.patch(
            f"/api/v1.0/orders/{response.json()['id']}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
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
        organization if there are several linked to the product.
        The one with the least active order count should be allocated.
        """
        course = factories.CourseFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[],
            target_courses=[target_course],
            price=0.00,
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=organizations
        )

        # Randomly create 9 orders for both organizations with random state and count
        # the number of active orders for each organization
        counter = {str(org.id): 0 for org in organizations}
        for _ in range(9):
            order = factories.OrderFactory(
                organization=random.choice(organizations),
                course=course,
                product=product,
                state=random.choice(enums.ORDER_STATE_CHOICES)[0],
            )

            if order.state != enums.ORDER_STATE_CANCELED:
                counter[str(order.organization.id)] += 1

        data = {
            "course_code": course.code,
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]

        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Order.objects.count(), 10)  # 9 + 1
        # The chosen organization should be one of the organizations with the lowest order count
        organization_id = models.Order.objects.get(id=order_id).organization.id
        self.assertEqual(counter[str(organization_id)], min(counter.values()))

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
        organization = product.course_relations.first().organizations.first()
        self.assertCountEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "id": uuid.uuid4(),
            "amount": 0.00,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order = models.Order.objects.get()
        order.submit(request=RequestFactory().request())
        # - Order has been successfully created and read_only_fields
        #   has been ignored.
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Order.objects.count(), 1)

        self.assertCountEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # - id, price and state has not been set according to data values
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": "panoramix",
                "product_id": str(product.id),
                "target_enrollments": [],
                "state": "validated",
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
                                    "datetime": course_run.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                    "call_to_action": course_run.state[
                                        "call_to_action"
                                    ],
                                    "text": course_run.state["text"],
                                },
                                "start": course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "end": course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
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
        )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(title="balançoire", price=0.00)
        cp_relation = factories.CourseProductRelationFactory(
            product=product, organizations=[organization]
        )
        course = factories.CourseFactory(title="mathématiques")
        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    'This order cannot be linked to the product "balançoire", '
                    'the course "mathématiques" and the organization "fun".'
                ]
            },
        )

        # Linking the course to the product should solve the problem
        cp_relation.course = course
        cp_relation.save()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
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
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    'This order cannot be linked to the product "balançoire", '
                    'the course "mathématiques" and the organization "fun".'
                ]
            },
        )

        # Linking the organization to the product should solve the problem
        product.course_relations.first().organizations.add(organization)
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(models.Order.objects.filter(organization=organization).exists())

    def test_api_order_create_authenticated_missing_product_then_course(self):
        """
        The payload must contain at least a product uid and a course code.
        """
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "product_id": ["This field is required."],
            },
        )

        product = factories.ProductFactory()
        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"product_id": str(product.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {"__all__": ["Either the course or the enrollment field is required."]},
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
        organization = product.course_relations.first().organizations.first()

        # User already owns an order for this product and course
        order = factories.OrderFactory(owner=user, course=course, product=product)

        data = {
            "product_id": str(product.id),
            "course_code": course.code,
            "organization_id": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": ["An order for this product and course already exists."]},
        )

        # But if we cancel the first order, user should be able to create a new order
        order.cancel()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_api_order_create_authenticated_billing_address_not_required(self):
        """
        When creating an order related to a fee product, if no billing address is
        given, the order is created as draft.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=200.0)
        organization = product.course_relations.first().organizations.first()

        data = {
            "product_id": str(product.id),
            "course_code": course.code,
            "organization_id": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 1)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_payment_binding(
        self, mock_create_payment, _mock_thumbnail
    ):
        """
        Create an order to a fee product and then submitting it should create a
        payment and bind payment information into the response.
        :
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }

        with self.assertNumQueries(22):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": user.username,
                "product_id": str(product.id),
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "state": "draft",
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
                                    "datetime": course_run.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                    "call_to_action": course_run.state[
                                        "call_to_action"
                                    ],
                                    "text": course_run.state["text"],
                                },
                                "start": course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "end": course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                    "+00:00", "Z"
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
        )
        with self.assertNumQueries(10):
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertDictEqual(
            response.json(),
            {
                "payment_info": {
                    "payment_id": f"pay_{order.id}",
                    "provider_name": "dummy",
                    "url": "http://testserver/api/v1.0/payments/notifications",
                }
            },
        )
        mock_create_payment.assert_called_once()

    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_payment_with_registered_credit_card(
        self,
        _mock_thumbnail,
        mock_create_one_click_payment,
    ):
        """
        Create an order to a fee product should create a payment. If user provides
        a credit card id, a one click payment should be triggered and within response
        payment information should contain `is_paid` property.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        credit_card = CreditCardFactory(owner=user)
        billing_address = BillingAddressDictFactory()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
            "credit_card_id": str(credit_card.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        expected_json = {
            "id": str(order.id),
            "certificate_id": None,
            "contract": None,
            "course": {
                "code": course.code,
                "id": str(course.id),
                "title": course.title,
                "cover": "_this_field_is_mocked",
            },
            "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "enrollment": None,
            "main_invoice_reference": None,
            "order_group_id": None,
            "organization_id": str(order.organization.id),
            "owner": user.username,
            "product_id": str(product.id),
            "total": float(product.price),
            "total_currency": settings.DEFAULT_CURRENCY,
            "state": "draft",
            "target_enrollments": [],
            "target_courses": [],
        }
        self.assertDictEqual(response.json(), expected_json)

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        mock_create_one_click_payment.assert_called_once()

        expected_json = {
            "payment_info": {
                "payment_id": f"pay_{order.id}",
                "provider_name": "dummy",
                "url": "http://testserver/api/v1.0/payments/notifications",
                "is_paid": True,
            },
        }
        self.assertDictEqual(response.json(), expected_json)

    @mock.patch.object(DummyPaymentBackend, "create_payment")
    def test_api_order_create_authenticated_payment_failed(self, mock_create_payment):
        """
        If payment creation failed, the order should not be created.
        """
        mock_create_payment.side_effect = CreatePaymentFailed("Unreachable endpoint")
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]

        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.exclude(state="draft").count(), 0)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(response.json(), {"detail": "Unreachable endpoint"})

    def test_api_order_create_authenticated_nb_seats(self):
        """
        The number of validated/pending orders on a product should not be above the limit
        set by the number of seats
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            state=enums.ORDER_STATE_VALIDATED,
            order_group=order_group,
        )
        data = {
            "course_code": course.code,
            "organization_id": str(relation.organizations.first().id),
            "order_group_id": str(order_group.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(21):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

    def test_api_order_create_authenticated_no_seats(self):
        """
        If nb_seats is set to 0 on an active order group, there should be no limit
        to the number of orders
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=0
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory.create_batch(
            size=100, product=product, course=course, order_group=order_group
        )
        data = {
            "course_code": course.code,
            "organization_id": str(relation.organizations.first().id),
            "order_group_id": str(order_group.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(47):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(
            models.Order.objects.filter(product=product, course=course).count(), 101
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_api_order_create_authenticated_free_product_no_billing_address(self):
        """
        Create an order on a free product without billing address
        should create an order then transition its state to 'validated'.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=0.00)
        organization = product.course_relations.first().organizations.first()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order = models.Order.objects.get(id=response.json()["id"])
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_create_authenticated_no_billing_address_to_validation(self):
        """
        Create an order on a fee product should be done in 3 steps.
        First create the order in draft state. Then submit the order by
        providing a billing address should pass the order state to `submitted`
        and return payment information. Once the payment has been done, the order
        should be validated.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()

        data = {
            "course_code": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order_id = response.json()["id"]
        billing_address = BillingAddressDictFactory()
        data["billing_address"] = billing_address
        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

        InvoiceFactory(order=order)
        order.validate()
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_create_order_group_required(self):
        """
        An order group must be passed when placing an order if the ordered product defines
        at least one active order group.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OrderGroup.objects.create(course_product_relation=relation, nb_seats=1)
        billing_address = BillingAddressDictFactory()
        data = {
            "course_code": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(17):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"An active order group is required for product {product.title}."
                ]
            },
        )
        self.assertFalse(
            models.Order.objects.filter(course=course, product=product).exists()
        )

    def test_api_order_create_order_group_unrelated(self):
        """The order group must apply to the product being ordered."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
        )
        billing_address = BillingAddressDictFactory()

        # Order group related to another product
        order_group = factories.OrderGroupFactory()

        data = {
            "course_code": relation.course.code,
            "order_group_id": str(order_group.id),
            "organization_id": str(organization.id),
            "product_id": str(relation.product.id),
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"This order group does not apply to the product {relation.product.title} "
                    f"and the course {relation.course.title}."
                ]
            },
        )
        self.assertFalse(models.Order.objects.exists())

    def test_api_order_create_several_order_groups(self):
        """A product can have several active order groups."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group1 = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        order_group2 = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            order_group=order_group1,
            state=random.choice(["submitted", "validated"]),
        )
        data = {
            "course_code": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        # Order group 1 should already be full
        response = self.client.post(
            "/api/v1.0/orders/",
            data={"order_group_id": str(order_group1.id), **data},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

        # Order group 2 should still have place
        response = self.client.post(
            "/api/v1.0/orders/",
            data={"order_group_id": str(order_group2.id), **data},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 2
        )

    def test_api_order_create_inactive_order_groups(self):
        """An inactive order group should not be taken into account."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1, is_active=False
        )
        billing_address = BillingAddressDictFactory()
        data = {
            "course_code": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )
