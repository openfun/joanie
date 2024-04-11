"""Tests for the Enrollment API."""

# pylint: disable=too-many-lines
import itertools
import json
import random
import uuid
from http import HTTPStatus
from logging import Logger
from unittest import mock

from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import enums, exceptions, factories, models
from joanie.core.factories import CourseRunFactory, EnrollmentFactory
from joanie.core.models import CourseState
from joanie.core.serializers import fields
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "FakeEdXAPIKey",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://edx:8073",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        }
    ]
)
class EnrollmentApiTest(BaseAPITestCase):
    """Test the API of the Enrollment object."""

    maxDiff = None

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def create_opened_course_run(self, count=1, **kwargs):
        """Create course runs opened for enrollment."""
        open_states = [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
        ]
        if count > 1:
            return CourseRunFactory.create_batch(
                count,
                state=random.choice(open_states),
                **kwargs,
            )

        return CourseRunFactory(
            state=random.choice(open_states),
            **kwargs,
        )

    def create_closed_course_run(self, count=1, **kwargs):
        """Create course runs closed for enrollment."""
        closed_states = [
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_CLOSED,
            CourseState.ONGOING_CLOSED,
            CourseState.ARCHIVED_CLOSED,
        ]
        if count > 1:
            return CourseRunFactory.create_batch(
                count,
                state=random.choice(closed_states),
                **kwargs,
            )

        return CourseRunFactory(
            state=random.choice(closed_states),
            **kwargs,
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_list_anonymous(self, _mock_set):
        """It should not be possible to retrieve the list of enrollments for anonymous users."""
        factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True)
        )

        response = self.client.get(
            "/api/v1.0/enrollments/",
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = json.loads(response.content)

        self.assertDictEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_read_list_authenticated_owned(self, *_):
        """Authenticated users retrieving the list of enrollments should only see theirs."""
        enrollment, other_enrollment = factories.EnrollmentFactory.create_batch(
            2, course_run=self.create_opened_course_run(is_listed=True)
        )

        # The user can see his/her enrollment
        token = self.generate_token_from_user(enrollment.user)

        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/enrollments/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(enrollment.id),
                        "certificate_id": None,
                        "course_run": {
                            "id": str(enrollment.course_run.id),
                            "course": {
                                "id": str(enrollment.course_run.course.id),
                                "code": str(enrollment.course_run.course.code),
                                "title": str(enrollment.course_run.course.title),
                                "cover": "_this_field_is_mocked",
                            },
                            "resource_link": enrollment.course_run.resource_link,
                            "title": enrollment.course_run.title,
                            "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                "+00:00", "Z"
                            )
                            if enrollment.course_run.state["priority"]
                            != CourseState.ARCHIVED_OPEN
                            else None,
                            "start": enrollment.course_run.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": enrollment.course_run.end.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "state": {
                                "priority": enrollment.course_run.state["priority"],
                                "text": enrollment.course_run.state["text"],
                                "call_to_action": enrollment.course_run.state[
                                    "call_to_action"
                                ],
                                "datetime": enrollment.course_run.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z")
                                if enrollment.course_run.state["datetime"]
                                else None,
                            },
                            "languages": enrollment.course_run.languages,
                        },
                        "created_on": enrollment.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "is_active": enrollment.is_active,
                        "orders": [],
                        "product_relations": [],
                        "state": enrollment.state,
                        "was_created_by_order": enrollment.was_created_by_order,
                    }
                ],
            },
        )

        # The user linked to the other enrollment can only see his/her enrollment
        token = self.generate_token_from_user(other_enrollment.user)

        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/enrollments/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(other_enrollment.id),
                        "certificate_id": None,
                        "course_run": {
                            "id": str(other_enrollment.course_run.id),
                            "course": {
                                "id": str(enrollment.course_run.course.id),
                                "code": str(other_enrollment.course_run.course.code),
                                "title": str(other_enrollment.course_run.course.title),
                                "cover": "_this_field_is_mocked",
                            },
                            "resource_link": other_enrollment.course_run.resource_link,
                            "title": other_enrollment.course_run.title,
                            "enrollment_start": other_enrollment.course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": other_enrollment.course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                "+00:00", "Z"
                            )
                            if other_enrollment.course_run.state["priority"]
                            != CourseState.ARCHIVED_OPEN
                            else None,
                            "start": other_enrollment.course_run.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": other_enrollment.course_run.end.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "state": {
                                "priority": other_enrollment.course_run.state[
                                    "priority"
                                ],
                                "text": other_enrollment.course_run.state["text"],
                                "call_to_action": other_enrollment.course_run.state[
                                    "call_to_action"
                                ],
                                "datetime": other_enrollment.course_run.state[
                                    "datetime"
                                ]
                                .isoformat()
                                .replace("+00:00", "Z")
                                if other_enrollment.course_run.state["datetime"]
                                else None,
                            },
                            "languages": other_enrollment.course_run.languages,
                        },
                        "created_on": other_enrollment.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "is_active": other_enrollment.is_active,
                        "orders": [],
                        "product_relations": [],
                        "state": other_enrollment.state,
                        "was_created_by_order": other_enrollment.was_created_by_order,
                    }
                ],
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_read_list_authenticated_with_certificate_products(self, *_):
        """
        When the related course run has certificate products they should be
        included in the response.
        """
        course_run, other_course_run = self.create_opened_course_run(
            count=2, is_listed=True
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run)
        product1, product2 = factories.ProductFactory.create_batch(
            2, type="certificate", courses=[course_run.course, other_course_run.course]
        )

        # Product types that should not be listed under an enrollment
        for ignored_type, _name in enums.PRODUCT_TYPE_CHOICES:
            if ignored_type == "certificate":
                continue
            factories.ProductFactory(type=ignored_type, courses=[course_run.course])

        # Create unrelated enrollments for the user in order to study db queries
        unrelated_run, unrelated_run_with_product = self.create_opened_course_run(
            count=2, is_listed=True
        )
        factories.ProductFactory(
            type="certificate", courses=[unrelated_run_with_product.course]
        )
        EnrollmentFactory(course_run=unrelated_run, user=enrollment.user)
        EnrollmentFactory(course_run=unrelated_run_with_product, user=enrollment.user)

        # The user can see his/her enrollment
        token = self.generate_token_from_user(enrollment.user)

        with self.assertNumQueries(17):
            self.client.get(
                "/api/v1.0/enrollments/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/enrollments/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = json.loads(response.content)
        self.assertEqual(len(content["results"]), 3)

        self.assertListEqual(
            content["results"][2]["product_relations"],
            [
                {
                    "id": str(product2.course_relations.last().id),
                    "order_groups": [],
                    "product": {
                        "instructions": "",
                        "call_to_action": "let's go!",
                        "certificate_definition": {
                            "description": "",
                            "name": str(product2.certificate_definition.name),
                            "title": str(product2.certificate_definition.title),
                        },
                        "contract_definition": None,
                        "id": str(product2.id),
                        "price": float(product2.price),
                        "price_currency": "EUR",
                        "state": {
                            "priority": product2.state["priority"],
                            "datetime": product2.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z")
                            if product2.state["datetime"]
                            else None,
                            "call_to_action": product2.state["call_to_action"],
                            "text": product2.state["text"],
                        },
                        "target_courses": [],
                        "title": product2.title,
                        "type": "certificate",
                    },
                },
                {
                    "id": str(product1.course_relations.last().id),
                    "order_groups": [],
                    "product": {
                        "instructions": "",
                        "call_to_action": "let's go!",
                        "certificate_definition": {
                            "description": "",
                            "name": str(product1.certificate_definition.name),
                            "title": str(product1.certificate_definition.title),
                        },
                        "contract_definition": None,
                        "state": {
                            "priority": product1.state["priority"],
                            "datetime": product1.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z")
                            if product1.state["datetime"]
                            else None,
                            "call_to_action": product1.state["call_to_action"],
                            "text": product1.state["text"],
                        },
                        "id": str(product1.id),
                        "price": float(product1.price),
                        "price_currency": "EUR",
                        "target_courses": [],
                        "title": product1.title,
                        "type": "certificate",
                    },
                },
            ],
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_list_authenticated_with_direct_certificate(
        self, _mock_set
    ):
        """
        When a certificate was emitted directly on this enrollment (without going through
        an order), it should be included in the payload.
        """
        course_run = self.create_opened_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(course_run=course_run)
        certificate = factories.EnrollmentCertificateFactory(enrollment=enrollment)

        # Create an unrelated enrollment in order to study db queries
        other_course_run = self.create_opened_course_run(is_listed=True)
        unrelated_enrollment = factories.EnrollmentFactory(course_run=other_course_run)
        factories.EnrollmentCertificateFactory(enrollment=unrelated_enrollment)

        # The user can see his/her enrollment
        token = self.generate_token_from_user(enrollment.user)

        with self.assertNumQueries(27):
            response = self.client.get(
                "/api/v1.0/enrollments/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = json.loads(response.content)

        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0]["certificate_id"],
            str(certificate.pk),
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_list_pagination(self, _mock_set):
        """Pagination should work as expected."""
        user = factories.UserFactory()
        enrollments = [
            factories.EnrollmentFactory(
                user=user, course_run=self.create_opened_course_run(is_listed=True)
            )
            for _ in range(3)
        ]
        enrollment_ids = [str(enrollment.id) for enrollment in enrollments]

        # The user can see his/her enrollment
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/enrollments/?page_size=2",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"],
            "http://testserver/api/v1.0/enrollments/?page=2&page_size=2",
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            enrollment_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/enrollments/?page_size=2&page=2",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"], "http://testserver/api/v1.0/enrollments/?page_size=2"
        )

        self.assertEqual(len(content["results"]), 1)
        enrollment_ids.remove(content["results"][0]["id"])
        self.assertEqual(enrollment_ids, [])

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_read_list_filtered_by_course_run_id(self, *_):
        """
        Authenticated users retrieving the list of enrollments should be able to filter
        by course run id.
        """
        user = factories.UserFactory()
        [course_run_1, course_run_2] = self.create_opened_course_run(2, is_listed=True)

        # User enrolls to both course runs
        enrollment_1 = factories.EnrollmentFactory(user=user, course_run=course_run_1)
        factories.EnrollmentFactory(user=user, course_run=course_run_2)

        token = self.generate_token_from_user(user)

        # Retrieve user's enrollment related to the first course_run
        response = self.client.get(
            f"/api/v1.0/enrollments/?course_run_id={str(course_run_1.id)}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(enrollment_1.id),
                        "certificate_id": None,
                        "course_run": {
                            "id": str(course_run_1.id),
                            "resource_link": course_run_1.resource_link,
                            "course": {
                                "id": str(course_run_1.course.id),
                                "code": str(course_run_1.course.code),
                                "title": str(course_run_1.course.title),
                                "cover": "_this_field_is_mocked",
                            },
                            "title": course_run_1.title,
                            "enrollment_start": course_run_1.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": course_run_1.enrollment_end.isoformat().replace(
                                "+00:00", "Z"
                            )
                            if course_run_1.state["priority"]
                            != CourseState.ARCHIVED_OPEN
                            else None,
                            "start": course_run_1.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": course_run_1.end.isoformat().replace("+00:00", "Z"),
                            "state": {
                                "priority": course_run_1.state["priority"],
                                "text": course_run_1.state["text"],
                                "call_to_action": course_run_1.state["call_to_action"],
                                "datetime": course_run_1.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z")
                                if course_run_1.state["datetime"]
                                else None,
                            },
                            "languages": course_run_1.languages,
                        },
                        "created_on": enrollment_1.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "is_active": enrollment_1.is_active,
                        "orders": [],
                        "product_relations": [],
                        "state": enrollment_1.state,
                        "was_created_by_order": enrollment_1.was_created_by_order,
                    }
                ],
            },
        )

    def test_api_enrollment_read_list_filtered_by_invalid_course_run_id(self):
        """
        Authenticated users providing an invalid course run id to filter its enrollments
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Retrieve user's enrollment related to the first course_run
        response = self.client.get(
            "/api/v1.0/enrollments/?course_run_id=invalid_course_run_id",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"course_run_id": ["Enter a valid UUID."]}
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_list_filtered_by_was_created_by_order(self, _mock_set):
        """
        Authenticated users retrieving the list of enrollments should be able to filter
        by was_created_by_order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        [cr1, cr2] = self.create_opened_course_run(2, is_listed=True)
        factories.EnrollmentFactory(
            user=user, course_run=cr1, was_created_by_order=False
        )
        factories.EnrollmentFactory(
            user=user, course_run=cr2, was_created_by_order=False
        )

        # Create an enrollment created by an order
        course = factories.CourseFactory()
        cr3 = self.create_opened_course_run(2, course=course, is_listed=True)[0]
        product = factories.ProductFactory(target_courses=[course])
        factories.OrderFactory(owner=user, product=product)
        factories.EnrollmentFactory(
            user=user, course_run=cr3, was_created_by_order=True
        )

        with self.assertNumQueries(49):
            response = self.client.get(
                "/api/v1.0/enrollments/?was_created_by_order=false",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        with self.assertNumQueries(27):
            response = self.client.get(
                "/api/v1.0/enrollments/?was_created_by_order=true",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_detail_anonymous(self, _mock_set):
        """Anonymous users should not be allowed to retrieve an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True),
        )

        response = self.client.get(f"/api/v1.0/enrollments/{enrollment.id}/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_read_detail_authenticated_owner_success(self, *_):
        """Authenticated users should be allowed to retrieve an enrollment they own."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        target_courses = factories.CourseFactory.create_batch(2)
        target_course_runs = self.create_opened_course_run(2, course=target_courses[0])
        self.create_opened_course_run(2, course=target_courses[1])
        factories.OrderFactory(
            owner=user,
            product__target_courses=target_courses,
            state=enums.ORDER_STATE_VALIDATED,
        )

        enrollment = factories.EnrollmentFactory(
            course_run=target_course_runs[0],
            user=user,
            is_active=True,
            was_created_by_order=True,
        )

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(enrollment.course_run.id),
                    "course": {
                        "id": str(enrollment.course_run.course.id),
                        "code": str(enrollment.course_run.course.code),
                        "title": str(enrollment.course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": enrollment.course_run.resource_link,
                    "title": enrollment.course_run.title,
                    "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if enrollment.course_run.state["priority"]
                    != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": enrollment.course_run.start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "end": enrollment.course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": enrollment.course_run.state["priority"],
                        "text": enrollment.course_run.state["text"],
                        "call_to_action": enrollment.course_run.state["call_to_action"],
                        "datetime": enrollment.course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if enrollment.course_run.state["datetime"]
                        else None,
                    },
                    "languages": enrollment.course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": enrollment.is_active,
                "orders": [],
                "product_relations": [],
                "state": enrollment.state,
                "was_created_by_order": enrollment.was_created_by_order,
            },
        )

    def test_api_enrollment_read_detail_authenticated_owner_certificate(self):
        """
        An enrollment's related certificate products and orders should be included in the payload.
        """
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN, is_listed=True
        )
        product = factories.ProductFactory(
            courses=[course_run.course], type="certificate"
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run)
        order = factories.OrderFactory(
            product=product, enrollment=enrollment, course=None
        )
        certificate = factories.OrderCertificateFactory(order=order)
        token = self.generate_token_from_user(order.owner)

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()

        self.assertListEqual(
            content["orders"],
            [
                {
                    "id": str(order.id),
                    "certificate_id": str(certificate.id),
                    "product_id": str(product.id),
                    "state": "draft",
                }
            ],
        )
        self.assertListEqual(
            content["product_relations"],
            [
                {
                    "id": str(product.course_relations.first().id),
                    "order_groups": [],
                    "product": {
                        "call_to_action": "let's go!",
                        "certificate_definition": {
                            "description": "",
                            "name": product.certificate_definition.name,
                            "title": product.certificate_definition.title,
                        },
                        "contract_definition": None,
                        "id": str(product.id),
                        "instructions": "",
                        "price": float(product.price),
                        "price_currency": "EUR",
                        "state": {
                            "call_to_action": None,
                            "datetime": None,
                            "priority": 7,
                            "text": "to be scheduled",
                        },
                        "target_courses": [],
                        "title": product.title,
                        "type": "certificate",
                    },
                },
            ],
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_read_detail_authenticated_not_owner(self, _mock_set):
        """Authenticated users should not be able to retrieve an enrollment they don't own."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True)
        )
        token = self.get_user_token("panoramix")

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertDictEqual(
            response.json(), {"detail": "No Enrollment matches the given query."}
        )

    def test_api_enrollment_create_anonymous(self):
        """Anonymous users should not be able to create an enrollment."""
        course_run = self.create_opened_course_run(is_listed=True)
        data = {"course_run_id": course_run.id, "was_created_by_order": False}
        response = self.client.post(
            "/api/v1.0/enrollments/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_create_authenticated_success(self, _, mock_set):
        """Any authenticated user should be able to create an enrollment."""
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(
            resource_link=resource_link, is_listed=True
        )
        data = {
            "course_run_id": str(course_run.id),
            "is_active": is_active,
            "was_created_by_order": False,
            "created_on": "2000-01-01T09:00:00+00:00",
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()

        self.assertEqual(models.Enrollment.objects.count(), 1)
        enrollment = models.Enrollment.objects.get()
        if is_active is True:
            mock_set.assert_called_once_with(enrollment)
        else:
            mock_set.assert_not_called()
        self.assertDictEqual(
            content,
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": is_active,
                "orders": [],
                "product_relations": [],
                "state": "set" if is_active else "",
                "was_created_by_order": False,
            },
        )
        self.assertNotIn("2000", content["created_on"])

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_api_enrollment_duplicate_course_run_with_order(self, _mock_set):
        """
        It should not be possible to enroll to course runs of the same course for a
        given order.
        """
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run1 = CourseRunFactory(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
            state=CourseState.ONGOING_OPEN,
        )
        course_run2 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course], price="0.00")
        order = factories.OrderFactory(owner=user, product=product)
        order.submit(request=RequestFactory().request())

        # Create a pre-existing enrollment and try to enroll to this course's second course run
        factories.EnrollmentFactory(
            course_run=course_run1, user=user, is_active=True, was_created_by_order=True
        )
        self.assertTrue(models.Enrollment.objects.filter(is_active=True).exists())
        data = {
            "course_run_id": course_run2.id,
            "is_active": True,
            "was_created_by_order": True,
        }
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {
                "user": [
                    "You are already enrolled to an opened course run "
                    f'for the course "{course_run2.course.title}".'
                ]
            },
        )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_create_authenticated_no_lms(self, _, mock_set, mock_logger):
        """
        If the resource link does not match any LMS, the enrollment should fail.
        """
        mock_set.return_value = True

        course_run = self.create_opened_course_run(
            resource_link="http://unknown.com/", is_listed=True
        )
        data = {
            "course_run_id": course_run.id,
            "is_active": True,
            "was_created_by_order": False,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        self.assertFalse(mock_set.called)
        enrollment = models.Enrollment.objects.get()
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": True,
                "orders": [],
                "product_relations": [],
                "state": "failed",
                "was_created_by_order": False,
            },
        )
        mock_logger.assert_called_once_with(
            'No LMS configuration found for course run: "%s".', "http://unknown.com/"
        )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_create_authenticated_enrollment_error(
        self, _, mock_set, mock_logger
    ):
        """
        If the enrollment on the LMS fails, the enrollment object should be marked as failed.
        """

        def enrollment_error(*args, **kwargs):
            raise exceptions.EnrollmentError()

        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        mock_set.side_effect = enrollment_error

        course_run = self.create_opened_course_run(
            resource_link=resource_link, is_listed=True
        )
        data = {
            "course_run_id": course_run.id,
            "is_active": True,
            "was_created_by_order": False,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        enrollment = models.Enrollment.objects.get()
        mock_set.assert_called_once_with(enrollment)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": True,
                "orders": [],
                "product_relations": [],
                "state": "failed",
                "was_created_by_order": False,
            },
        )
        mock_logger.assert_called_once_with(
            'Enrollment failed for course run "%s".', course_run.resource_link
        )

    def test_api_enrollment_create_authenticated_missing_is_active(self):
        """
        An authenticated user trying to enroll via the API, should get a 400 error
        if the "is_active" field is missing.
        """
        course_run = self.create_opened_course_run(is_listed=True)
        data = {"course_run_id": course_run.id, "was_created_by_order": False}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {"is_active": ["This field is required."]},
        )
        self.assertFalse(models.Enrollment.objects.exists())

    def test_api_enrollment_create_authenticated_missing_was_created_by_order(self):
        """
        An authenticated user trying to enroll via the API, should get a 400 error
        if the "is_active" field is missing.
        """
        course_run = self.create_opened_course_run(is_listed=True)
        data = {"course_run_id": course_run.id, "is_active": True}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {"was_created_by_order": ["This field is required."]},
        )
        self.assertFalse(models.Enrollment.objects.exists())

    def test_api_enrollment_create_authenticated_owner_not_matching(self):
        """
        An authenticated user should not be allowed to create an enrollment linked
        to an order that he/she does not own.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        factories.OrderFactory(product=product)
        course_run = target_course_runs[0]
        data = {
            "course_run_id": course_run.id,
            "is_active": True,
            "was_created_by_order": True,
        }
        token = self.get_user_token("another-username")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'Course run "{course_run.id}" requires a valid order to enroll.'
                ]
            },
        )
        self.assertFalse(models.Enrollment.objects.exists())

    def test_api_enrollment_create_authenticated_matching_unvalidated_order(self):
        """
        It should not be allowed to create an enrollment with an order that is
        not validated for a course linked to a product.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        order = factories.OrderFactory(
            product=product,
            state=random.choice(
                [enums.ORDER_STATE_PENDING, enums.ORDER_STATE_CANCELED]
            ),
        )
        data = {
            "course_run_id": target_course_runs[0].id,
            "is_active": True,
            "was_created_by_order": True,
        }
        token = self.generate_token_from_user(order.owner)

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        course_run_id = target_course_runs[0].id
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'Course run "{course_run_id}" requires a valid order to enroll.'
                ]
            },
        )

    def test_api_enrollment_create_authenticated_matching_no_order(self):
        """
        It should not be allowed to create an enrollment without an order for a course
        linked to a product.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        data = {
            "course_run_id": target_course_runs[0].id,
            "is_active": True,
            "was_created_by_order": True,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        course_run_id = target_course_runs[0].id
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'Course run "{course_run_id}" requires a valid order to enroll.'
                ]
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_create_has_read_only_fields(self, _, mock_set):
        """
        When user creates an enrollment, it should not be allowed
        to set "id", "state" fields
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(
            resource_link=resource_link, is_listed=True
        )
        data = {
            "course_run_id": course_run.id,
            "id": uuid.uuid4(),
            "is_active": is_active,
            "state": enums.ENROLLMENT_STATE_FAILED,
            "was_created_by_order": False,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        enrollment = models.Enrollment.objects.get()
        if is_active is True:
            mock_set.assert_called_once_with(enrollment)
        else:
            mock_set.assert_not_called()

        # - Enrollment uid has been generated and state has been set according
        #   to LMSHandler.set_enrollment response
        self.assertNotEqual(enrollment.id, data["id"])
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": is_active,
                "orders": [],
                "product_relations": [],
                "state": "set" if is_active else "",
                "was_created_by_order": False,
            },
        )

    def test_api_enrollment_create_for_closed_course_run(self):
        """An authenticated user should not be allowed to enroll to a closed course run."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        target_course = factories.CourseFactory()
        course_run = self.create_closed_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )

        data = {
            "course_run_id": course_run.id,
            "is_active": True,
            "was_created_by_order": False,
        }

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    "You are not allowed to enroll to a course run not opened for enrollment."
                ]
            },
        )

    def test_api_enrollment_create_with_unknown_course_run(self):
        """An authenticated user should not be allowed to enroll to an unknown course run."""

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course_run = factories.CourseRunFactory.build()
        data = {
            "course_run_id": str(course_run.id),
            "is_active": True,
            "was_created_by_order": False,
        }

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    ("A course run with id " f'"{course_run.id}" does not exist.')
                ]
            },
        )

    def test_api_enrollment_create_with_wrong_course_run_payload(self):
        """Creating an enroll with a wrong course_run parameter should fail."""

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        course_run = self.create_opened_course_run(is_listed=True)
        data = {
            "course_run": str(course_run.id),
            "is_active": True,
            "was_created_by_order": False,
        }

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(),
            {"__all__": ["You must provide a course_run_id to create an enrollment."]},
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_delete_anonymous(self, _mock_set):
        """Anonymous users should not be able to delete an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True)
        )

        response = self.client.delete(f"/api/v1.0/enrollments/{enrollment.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

        self.assertEqual(models.Enrollment.objects.count(), 1)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_delete_authenticated(self, _mock_set):
        """
        Authenticated users should not be able to delete any enrollment
        whether he/she is staff or even superuser.
        """
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True)
        )
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(models.Enrollment.objects.count(), 1)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_delete_owner(self, _mock_set):
        """A user should not be allowed to delete his/her enrollments."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(is_listed=True)
        )
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.delete(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(models.Enrollment.objects.count(), 1)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_update_detail_state_anonymous(self, _mock_set):
        """
        Anonymous users should not be allowed to update the state of an
        enrollment.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )
        # Try setting state starting from any state and going to any state
        for i, (old_state, new_state) in enumerate(
            itertools.product(enums.ENROLLMENT_STATE_CHOICES, repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i), is_listed=True
                ),
                state=old_state[0],
            )

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"state": new_state[0]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

            self.assertDictEqual(
                response.json(),
                {"detail": "Authentication credentials were not provided."},
            )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_update_detail_state_not_owner(self, _mock_set):
        """
        An authenticated user should not be allowed to update the state of an
        enrollment he/she doesn't own, even if he/she is staff or superuser.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )

        # Try setting "is_active" starting from any value of the field
        for i, (is_active_old, is_active_new) in enumerate(
            itertools.product([True, False], repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i), is_listed=True
                ),
                is_active=is_active_old,
            )

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"is_active": is_active_new},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

            self.assertDictEqual(
                response.json(), {"detail": "No Enrollment matches the given query."}
            )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_update_detail_is_active_owner(self, _mock_set, _):
        """
        The user should be able to update the "is_active" field on his/her enrollments.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )
        # Try setting "is_active" starting from any value of the field
        for i, (is_active_old, is_active_new) in enumerate(
            itertools.product([True, False], repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i), is_listed=True
                ),
                is_active=is_active_old,
                state="",
            )
            token = self.generate_token_from_user(enrollment.user)

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"is_active": is_active_new},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

            self.assertDictEqual(
                response.json(),
                {
                    "id": str(enrollment.id),
                    "certificate_id": None,
                    "course_run": {
                        "id": str(enrollment.course_run.id),
                        "course": {
                            "id": str(enrollment.course_run.course.id),
                            "code": str(enrollment.course_run.course.code),
                            "title": str(enrollment.course_run.course.title),
                            "cover": "_this_field_is_mocked",
                        },
                        "resource_link": enrollment.course_run.resource_link,
                        "title": enrollment.course_run.title,
                        "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                            "+00:00", "Z"
                        ),
                        "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(
                            "+00:00", "Z"
                        )
                        if enrollment.course_run.state["priority"]
                        != CourseState.ARCHIVED_OPEN
                        else None,
                        "start": enrollment.course_run.start.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "end": enrollment.course_run.end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "state": {
                            "priority": enrollment.course_run.state["priority"],
                            "text": enrollment.course_run.state["text"],
                            "call_to_action": enrollment.course_run.state[
                                "call_to_action"
                            ],
                            "datetime": enrollment.course_run.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z")
                            if enrollment.course_run.state["datetime"]
                            else None,
                        },
                        "languages": enrollment.course_run.languages,
                    },
                    "created_on": enrollment.created_on.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "is_active": is_active_new,
                    "orders": [],
                    "product_relations": [],
                    "state": ""
                    if is_active_old is False and is_active_new is False
                    else "set",
                    "was_created_by_order": False,
                },
            )

    # pylint: disable=too-many-locals
    def _check_api_enrollment_update_detail(self, enrollment, user, http_code):
        """Nobody should be allowed to update an enrollment."""
        user_token = self.generate_token_from_user(enrollment.user)

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )
        initial_data = json.loads(response.content)
        self.assertEqual(initial_data["state"], enrollment.state)

        # Get alternative values to try to modify our enrollment
        other_user = factories.UserFactory(is_superuser=random.choice([True, False]))
        factories.OrderFactory(
            owner=other_user,
            product=enrollment.course_run.course.targeted_by_products.first(),
            state=enums.ORDER_STATE_VALIDATED,
        )

        # Try modifying the enrollment on each field with our alternative data
        course_run = models.CourseRun.objects.exclude(id=enrollment.course_run_id).get()
        new_state = random.choice([s[0] for s in enums.ENROLLMENT_STATE_CHOICES])
        new_data = {
            "id": uuid.uuid4(),
            "user": other_user.username,
            "course_run_id": course_run.id,
            "created_on": "2000-01-01T09:00:00+00:00",
            "state": new_state,
            "was_created_by_order": False,
        }
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.generate_token_from_user(user)}"}
            if user
            else {}
        )

        response = self.client.patch(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data=new_data,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, http_code)

        # Check that nothing was modified
        self.assertEqual(models.Enrollment.objects.count(), 1)
        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )
        actual_data = json.loads(response.content)
        self.assertEqual(
            actual_data.pop("state"),
            "set" if http_code == HTTPStatus.OK else initial_data["state"],
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_anonymous(self, _mock_set):
        """An anonymous user should not be allowed to update any enrollment."""
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_VALIDATED
        )
        enrollment = factories.EnrollmentFactory(
            course_run=course_run1,
            user=order.owner,
            is_active=True,
            was_created_by_order=True,
        )
        self._check_api_enrollment_update_detail(
            enrollment, None, HTTPStatus.UNAUTHORIZED
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_authenticated_superuser(self, _mock_set):
        """A superuser should not be allowed to update any enrollment."""
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_VALIDATED
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run1,
            user=order.owner,
            is_active=True,
            was_created_by_order=True,
        )
        self._check_api_enrollment_update_detail(enrollment, user, HTTPStatus.NOT_FOUND)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_authenticated_owner(self, _mock_set):
        """An authenticated user should not be allowed to update his/her enrollment."""
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        factories.OrderFactory(
            owner=user,
            product__target_courses=[target_course],
            state=enums.ORDER_STATE_VALIDATED,
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run1, user=user, is_active=True, was_created_by_order=True
        )
        self._check_api_enrollment_update_detail(enrollment, user, HTTPStatus.OK)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_unenroll_authenticated_owner(self, _, __):
        """
        An authenticated user should be allowed to update its enrollment to unenroll.
        """
        user = factories.UserFactory()
        user_token = self.generate_token_from_user(user)
        course_run = self.create_opened_course_run(
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, user=user, is_active=True
        )

        response = self.client.put(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data={
                "is_active": False,
                "was_created_by_order": enrollment.was_created_by_order,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": False,
                "orders": [],
                "product_relations": [],
                "state": "set",
                "was_created_by_order": False,
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_update_was_created_by_order_on_inactive_enrollment(
        self, _, __
    ):
        """
        An authenticated user should be allowed to update the was_created_by_order field
        of one of its enrollment if this one was previously inactive.
        """
        user = factories.UserFactory()
        user_token = self.generate_token_from_user(user)
        course_run = self.create_opened_course_run(
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, user=user, is_active=True
        )

        self.assertEqual(enrollment.is_active, True)
        self.assertEqual(enrollment.was_created_by_order, False)

        # User unenrolls and tried to update the was_created_by_order field but it should
        # not be updated because enrollment is active.
        response = self.client.put(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data={
                "is_active": False,
                "was_created_by_order": True,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": False,
                "orders": [],
                "product_relations": [],
                "state": "set",
                "was_created_by_order": False,
            },
        )

        # Then user purchases a product containing the previously created course run and
        # tries to update to was_created_by_order field again.
        product = factories.ProductFactory(target_courses=[course_run.course])
        order = factories.OrderFactory(
            owner=user, product=product, state=enums.ORDER_STATE_SUBMITTED
        )

        # - Create an invoice related to the order to mark it as validated and trigger the
        #   auto enrollment logic on validate transition
        InvoiceFactory(order=order, total=order.total)
        order.validate()

        # The enrollment should have been activated automatically
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_active)

        # Set it to False and show that the `was_created_by_order` flag can then be updated
        enrollment.is_active = False
        enrollment.save()

        response = self.client.put(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data={
                "is_active": True,
                "was_created_by_order": True,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": True,
                "orders": [],
                "product_relations": [],
                "state": "set",
                "was_created_by_order": True,
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_update_was_created_by_order_on_order_enrollment(
        self, _, __
    ):
        """
        An authenticated user should not be allowed to update the "was_created_by_order" field
        to False on one of its enrollment if this one was previously created by an
        order and active.
        """
        user = factories.UserFactory()
        user_token = self.generate_token_from_user(user)
        target_course = factories.CourseFactory()
        course_run = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
            is_listed=True,
        )
        self.create_opened_course_run(course=target_course)
        factories.OrderFactory(
            owner=user,
            product__target_courses=[target_course],
            state=enums.ORDER_STATE_VALIDATED,
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run, user=user, is_active=True, was_created_by_order=True
        )

        self.assertEqual(enrollment.is_active, True)
        self.assertEqual(enrollment.was_created_by_order, True)

        # User unenrolls and tried to update the was_created_by_order field, but it
        # should not be updated because enrollment is active.
        response = self.client.put(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data={
                "is_active": True,
                "was_created_by_order": False,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": True,
                "orders": [],
                "product_relations": [],
                "state": "set",
                "was_created_by_order": True,
            },
        )

        # Then user purchases a product containing the previously created course run and
        # tries to update to was_created_by_order field again.
        factories.CourseRunFactory(course=course_run.course)
        factories.OrderFactory(
            owner=user,
            product__target_courses=[course_run.course],
            state=enums.ORDER_STATE_VALIDATED,
        )

        response = self.client.put(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data={
                "is_active": True,
                "was_created_by_order": True,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "certificate_id": None,
                "course_run": {
                    "id": str(course_run.id),
                    "course": {
                        "id": str(course_run.course.id),
                        "code": str(course_run.course.code),
                        "title": str(course_run.course.title),
                        "cover": "_this_field_is_mocked",
                    },
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if course_run.state["priority"] != CourseState.ARCHIVED_OPEN
                    else None,
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course_run.state["datetime"]
                        else None,
                    },
                    "languages": course_run.languages,
                },
                "created_on": enrollment.created_on.isoformat().replace("+00:00", "Z"),
                "is_active": True,
                "orders": [],
                "product_relations": [],
                "state": "set",
                "was_created_by_order": True,
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_enrollment_filter_by_query_course_title(self, _, __):
        """
        Authenticated users retrieving the list of enrollments should be able to filter
        by course title if he is enrolled to the course run.
        """
        open_states = [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
        ]
        user = factories.UserFactory()
        course_1 = factories.CourseFactory(title="Introduction to resource filtering")
        course_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de ressource"
        )
        course_2 = factories.CourseFactory(title="Advanced aerodynamic flows")
        course_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        course_3 = factories.CourseFactory(title="Rubber management on a single-seater")
        course_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )
        # Create course run 1, 2 and 3
        course_run_1 = CourseRunFactory(
            course=course_1, state=random.choice(open_states), is_listed=True
        )
        course_run_2 = CourseRunFactory(
            course=course_2, state=random.choice(open_states), is_listed=True
        )
        course_run_3 = CourseRunFactory(
            course=course_3, state=random.choice(open_states), is_listed=True
        )
        # User enrolls to two course_runs out of three
        enrollment_1 = factories.EnrollmentFactory(user=user, course_run=course_run_1)
        enrollment_2 = factories.EnrollmentFactory(user=user, course_run=course_run_2)
        token = self.generate_token_from_user(user)

        # without parsing a query string, we should find both enrollments of the user
        response = self.client.get(
            "/api/v1.0/enrollments/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(enrollment_1.id), str(enrollment_2.id)],
        )

        # Prepare queries to test
        queries = [
            "Flux aérodynamiques avancés",
            "Flux+aérodynamiques+avancés",
            "aérodynamiques",
            "aerodynamic",
            "aéro",
            "aero",
            "aer",
            "advanced",
            "flows",
            "flo",
            "Advanced aerodynamic flows",
            "dynamic",
            "ows",
            "av",
            "ux",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/enrollments/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0].get("id"), str(enrollment_2.id))

        # User attempts to search on the course run where he did not enroll
        response = self.client.get(
            f"/api/v1.0/enrollments/?query={str(course_run_3.course.title)}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # User attempts to search with a course title that does not exist at all
        response = self.client.get(
            "/api/v1.0/enrollments/?query=veryFakeCourseTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)
