"""
Test suite for order flows.
"""

# pylint: disable=too-many-lines,too-many-public-methods
import json
from datetime import date
from http import HTTPStatus
from unittest import mock

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

import responses
from stockholm import Money
from viewflow.fsm import TransitionNotAllowed

from joanie.core import enums, exceptions, factories
from joanie.core.factories import CourseRunFactory
from joanie.core.models import CourseState, Enrollment
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.dummy import DummyLMSBackend
from joanie.lms_handler.backends.openedx import (
    OPENEDX_MODE_HONOR,
    OPENEDX_MODE_VERIFIED,
)
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.tests.base import BaseLogMixinTestCase


class OrderFlowsTestCase(TestCase, BaseLogMixinTestCase):
    """Test suite for the Order flow."""

    maxDiff = None

    def test_flow_order_assign(self):
        """
        It should set the order state to ORDER_STATE_TO_SAVE_PAYMENT_METHOD
        when the order has no credit card.
        """
        order = factories.OrderFactory(credit_card=None)

        order.init_flow(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)

    def test_flow_order_assign_free_product(self):
        """
        It should set the order state to ORDER_STATE_COMPLETED
        when the order has a free product.
        """
        order = factories.OrderFactory(product__price=0)

        order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flow_order_assign_no_billing_address(self):
        """
        It should raise a TransitionNotAllowed exception
        when the order has no billing address and the order is not free.
        """
        order = factories.OrderFactory()

        with self.assertRaises(ValidationError):
            order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_ASSIGNED)

    def test_flow_order_assign_no_organization(self):
        """
        It should raise a TransitionNotAllowed exception
        when the order has no organization.
        """
        order = factories.OrderFactory(organization=None)

        with self.assertRaises(TransitionNotAllowed):
            order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_flows_order_cancel(self):
        """
        Order has a cancel method which is in charge to unroll owner to all active
        related enrollments if related course is not listed
        then switch the `state` property to cancel.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )[0]

        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course], price=0.00
        )
        order = factories.OrderFactory(
            owner=owner,
            product=product,
            course=course,
        )
        order.init_flow()

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(
            course_run=cr1, user=owner, is_active=True, was_created_by_order=True
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should be unenrolled to related enrollments
        order.flow.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=False).count(), 1)

    def test_flows_order_cancel_with_course_implied_in_several_products(self):
        """
        On order cancellation, if the user owns other products which order's enrollments
        also rely on, it should not be unenrolled.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )[0]

        # - Create 2 products which relies on the same course
        [product_1, product_2] = factories.ProductFactory.create_batch(
            2,
            courses=[course],
            target_courses=[target_course],
            price=0.00,
        )
        # - User purchases the two products
        order = factories.OrderFactory(
            owner=owner,
            product=product_1,
            course=course,
        )
        order.init_flow()
        factories.OrderFactory(owner=owner, product=product_2, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(
            course_run=cr1, user=owner, is_active=True, was_created_by_order=True
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should not be unenrolled from related enrollments
        with self.assertNumQueries(13):
            order.flow.cancel()

        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_flows_order_cancel_with_listed_course_run(self):
        """
        On order cancellation, if order's enrollment relies on course with `is_listed`
        attribute set to True, user should not be unenrolled.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )[0]

        # - Create one product which relies on the same course
        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course], price=0.00
        )
        # - User purchases the two products
        order = factories.OrderFactory(owner=owner, product=product, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(course_run=cr1, user=owner, is_active=True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should not be unenrolled to related enrollments
        with self.assertNumQueries(10):
            order.flow.cancel()

        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_flows_order_complete_transition_success(self):
        """
        Test that the complete transition is successful
        when the order is free or has invoices and is in the
        ORDER_STATE_PENDING state
        """
        order_invoice = factories.OrderFactory(
            product=factories.ProductFactory(price="10.00"),
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "10.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )
        self.assertEqual(order_invoice.flow._can_be_state_completed(), True)  # pylint: disable=protected-access
        order_invoice.flow.complete()
        self.assertEqual(order_invoice.state, enums.ORDER_STATE_COMPLETED)

        order_free = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=enums.ORDER_STATE_DRAFT,
        )
        order_free.init_flow()

        self.assertEqual(order_free.flow._can_be_state_completed(), True)  # pylint: disable=protected-access
        # order free are automatically completed without calling the complete method
        # but submit need to be called nonetheless
        self.assertEqual(order_free.state, enums.ORDER_STATE_COMPLETED)
        with self.assertRaises(TransitionNotAllowed):
            order_free.flow.complete()

    def test_flows_order_complete_failure(self):
        """
        Test that the complete transition fails when the
        order is not free and has no invoices
        """
        order_no_invoice = factories.OrderFactory(
            product=factories.ProductFactory(price="10.00"),
            state=enums.ORDER_STATE_PENDING,
        )
        self.assertEqual(order_no_invoice.flow._can_be_state_completed(), False)  # pylint: disable=protected-access
        with self.assertRaises(TransitionNotAllowed):
            order_no_invoice.flow.complete()
        self.assertEqual(order_no_invoice.state, enums.ORDER_STATE_PENDING)

    def test_flows_order_complete_failure_when_not_pending(self):
        """
        Test that the complete transition fails when the
        order is not in the ORDER_STATE_PENDING state
        """
        order = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=enums.ORDER_STATE_COMPLETED,
        )
        self.assertEqual(order.flow._can_be_state_completed(), True)  # pylint: disable=protected-access
        with self.assertRaises(TransitionNotAllowed):
            order.flow.complete()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://openedx.test",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
                "SELECTOR_REGEX": r".*",
            }
        ]
    )
    def test_flows_order_validate_auto_enroll(self):
        """
        When an order is validated, if one target course contains only one course run
        and this one is opened for enrollment, the user should be automatically enrolled
        """
        course = factories.CourseFactory()
        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        user = factories.UserFactory()
        factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        url = f"http://openedx.test/api/enrollment/v1/enrollment/{user.username},{course_id}"
        responses.add(
            responses.GET,
            url,
            status=HTTPStatus.OK,
            json={"is_active": False, "mode": OPENEDX_MODE_HONOR},
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.OK,
            json={"is_active": True},
        )

        # Create an order
        order = factories.OrderFactory(product=product, owner=user)
        order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, url)
        self.assertEqual(
            responses.calls[1].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        enrollment = Enrollment.objects.get(
            user=order.owner, course_run__resource_link=resource_link
        )
        self.assertEqual(enrollment.state, "set")
        self.assertEqual(
            json.loads(responses.calls[1].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": OPENEDX_MODE_VERIFIED,
                "user": enrollment.user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    def test_flows_order_validate_auto_enroll_failure(self):
        """
        When an order is validated, if one target course contains only one course run
        and this one is opened for enrollment, the user should be automatically enrolled
        If the enrollment creation fails, the order should be validated.
        """
        course = factories.CourseFactory()
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        course_run = factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(price="0.00")
        factories.ProductTargetCourseRelationFactory(
            product=product, course=course, course_runs=[course_run]
        )

        user = factories.UserFactory()
        # Create an enrollment on other opened course run on this course
        factories.EnrollmentFactory(
            course_run__course=course,
            course_run__resource_link=(
                "http://openedx.test/courses/course-v1:edx+000001+Demo_Course2/course"
            ),
            course_run__state=CourseState.ONGOING_OPEN,
            course_run__is_listed=True,
            is_active=True,
            user=user,
        )
        self.assertEqual(Enrollment.objects.count(), 1)

        # Create an order
        order = factories.OrderFactory(product=product, owner=user)
        order.init_flow()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(Enrollment.objects.count(), 1)

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://openedx.test",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
                "SELECTOR_REGEX": r".*",
            }
        ]
    )
    def test_flows_order_validate_auto_enroll_edx_failure(self):
        """
        When an order is validated, if one target course contains only one course run
        and this one is opened for enrollment, the user should be automatically enrolled
        If the enrollment request fails, the order should be validated.
        """
        course = factories.CourseFactory()
        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        user = factories.UserFactory()
        factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        url = f"http://openedx.test/api/enrollment/v1/enrollment/{user.username},{course_id}"
        responses.add(
            responses.GET,
            url,
            status=HTTPStatus.OK,
            json={"is_active": False, "mode": OPENEDX_MODE_HONOR},
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.BAD_REQUEST,
            json=None,
        )

        # Create an order
        order = factories.OrderFactory(product=product, owner=user)
        order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, url)
        self.assertEqual(
            responses.calls[1].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        enrollment = Enrollment.objects.get(
            user=order.owner, course_run__resource_link=resource_link
        )
        self.assertEqual(enrollment.state, "failed")
        self.assertEqual(
            json.loads(responses.calls[1].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": OPENEDX_MODE_VERIFIED,
                "user": enrollment.user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://openedx.test",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
                "SELECTOR_REGEX": r".*",
            }
        ]
    )
    def test_flows_order_complete_preexisting_enrollments_targeted(self):
        """
        When an order is completed, if the user was previously enrolled for free in any of the
        course runs targeted by the purchased product, we should change their enrollment mode on
        these course runs to "verified".
        """
        course = factories.CourseFactory()
        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        course_run = factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )
        factories.CourseRunFactory(
            course=course, state=CourseState.ONGOING_OPEN, is_listed=True
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")
        user = factories.UserFactory()

        url = f"http://openedx.test/api/enrollment/v1/enrollment/{user.username},{course_id}"
        responses.add(
            responses.GET,
            url,
            status=HTTPStatus.OK,
            json={"is_active": True, "mode": OPENEDX_MODE_HONOR},
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.OK,
            json={"is_active": True},
        )

        # Create random enrollment on the same course
        factories.EnrollmentFactory(course_run=course_run, is_active=True)
        responses.reset()

        # Create a pre-existing free enrollment
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, is_active=True, user=user
        )
        order = factories.OrderFactory(product=product, owner=user)
        order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 4)
        self.assertEqual(responses.calls[3].request.url, url)
        self.assertEqual(
            responses.calls[3].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[3].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": OPENEDX_MODE_VERIFIED,
                "user": order.owner.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            }
        ]
    )
    def test_flows_order_complete_preexisting_enrollments_targeted_moodle(self):
        """
        When an order is completed, if the user was previously enrolled for free in any of the
        course runs targeted by the purchased product, we should change their enrollment mode on
        these course runs to "verified".
        """
        course = factories.CourseFactory()
        resource_link = "http://moodle.test/course/view.php?id=2"
        course_run = factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )
        factories.CourseRunFactory(
            course=course, state=CourseState.ONGOING_OPEN, is_listed=True
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")
        backend = LMSHandler.select_lms(resource_link)

        responses.add(
            responses.POST,
            backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "users": [
                    {
                        "id": 5,
                        "username": "student",
                        "firstname": "Student",
                        "lastname": "User",
                        "fullname": "Student User",
                        "email": "student@example.com",
                        "department": "",
                        "firstaccess": 1704716076,
                        "lastaccess": 1704716076,
                        "auth": "manual",
                        "suspended": False,
                        "confirmed": True,
                        "lang": "en",
                        "theme": "",
                        "timezone": "99",
                        "mailformat": 1,
                        "description": "",
                        "descriptionformat": 1,
                        "profileimageurlsmall": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
                        ),
                        "profileimageurl": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1"
                        ),
                    }
                ],
                "warnings": [],
            },
        )

        responses.add(
            responses.POST,
            backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=[
                {
                    "id": 5,
                    "name": "",
                    "shortname": "student",
                    "description": "",
                    "sortorder": 5,
                    "archetype": "student",
                },
            ],
        )

        responses.add(
            responses.POST,
            backend.build_url("enrol_manual_enrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": "2",
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        # Create a pre-existing free enrollment
        factories.EnrollmentFactory(
            course_run=course_run, user__username="student", is_active=True
        )
        order = factories.OrderFactory(product=product, owner__username="student")

        order.init_flow()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 3)

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            }
        ]
    )
    def test_flows_order_validate_auto_enroll_moodle_failure(self):
        """
        When an order is validated, if one target course contains only one course run
        and this one is opened for enrollment, the user should be automatically enrolled
        If the enrollment request fails, the order should be validated.
        """
        course = factories.CourseFactory()
        resource_link = "http://moodle.test/course/view.php?id=2"
        factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")
        backend = LMSHandler.select_lms(resource_link)

        responses.add(
            responses.POST,
            backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=[
                {
                    "id": 5,
                    "name": "",
                    "shortname": "student",
                    "description": "",
                    "sortorder": 5,
                    "archetype": "student",
                },
            ],
        )

        responses.add(
            responses.POST,
            backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.NOT_FOUND,
        )

        responses.add(
            responses.POST,
            backend.build_url("core_user_create_user"),
            status=HTTPStatus.BAD_REQUEST,
        )

        responses.add(
            responses.POST,
            backend.build_url("enrol_manual_enrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": "2",
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        # - Submit the order to trigger the validation as it is free
        order = factories.OrderFactory(product=product)
        order.init_flow()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 3)

    def test_flows_order_cancel_success(self):
        """Test that the cancel transition is successful from any state"""
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderFactory(state=state)
                order.flow.cancel()
                self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    @responses.activate
    def test_flows_order_cancel_certificate_product_openedx_enrollment_mode(self):
        """
        Test that the source enrollment is set back to "honor" in the LMS when a related order
        is canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type="certificate")

        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            course_run__course=course,
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__resource_link=resource_link,
            user=user,
            is_active=True,
        )
        order = factories.OrderFactory(
            course=None,
            product=product,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
            owner=user,
        )

        url = f"http://openedx.test/api/enrollment/v1/enrollment/{user.username},{course_id}"
        responses.add(
            responses.GET,
            url,
            status=HTTPStatus.OK,
            json={"is_active": enrollment.is_active, "mode": OPENEDX_MODE_VERIFIED},
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.OK,
            json={"is_active": enrollment.is_active},
        )

        with override_settings(
            JOANIE_LMS_BACKENDS=[
                {
                    "API_TOKEN": "a_secure_api_token",
                    "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                    "BASE_URL": "http://openedx.test",
                    "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
                    "SELECTOR_REGEX": r".*",
                }
            ]
        ):
            order.flow.cancel()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.state, "set")

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, url)
        self.assertEqual(
            responses.calls[1].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[1].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": OPENEDX_MODE_HONOR,
                "user": enrollment.user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            }
        ]
    )
    def test_flows_order_cancel_certificate_product_moodle(self):
        """
        Test that the source enrollment is set back to "honor" in the LMS when a related order
        is canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type="certificate")

        resource_link = "http://moodle.test/course/view.php?id=2"

        enrollment = factories.EnrollmentFactory(
            course_run__course=course,
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__resource_link=resource_link,
            is_active=True,
        )
        order = factories.OrderFactory(
            course=None,
            product=product,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
        )

        backend = LMSHandler.select_lms(resource_link)

        responses.add(
            responses.POST,
            backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": enrollment.user.username,
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "users": [
                    {
                        "id": 5,
                        "username": "student",
                        "firstname": "Student",
                        "lastname": "User",
                        "fullname": "Student User",
                        "email": "student@example.com",
                        "department": "",
                        "firstaccess": 1704716076,
                        "lastaccess": 1704716076,
                        "auth": "manual",
                        "suspended": False,
                        "confirmed": True,
                        "lang": "en",
                        "theme": "",
                        "timezone": "99",
                        "mailformat": 1,
                        "description": "",
                        "descriptionformat": 1,
                        "profileimageurlsmall": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
                        ),
                        "profileimageurl": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1"
                        ),
                    }
                ],
                "warnings": [],
            },
        )

        responses.add(
            responses.POST,
            backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=[
                {
                    "id": 5,
                    "name": "",
                    "shortname": "student",
                    "description": "",
                    "sortorder": 5,
                    "archetype": "student",
                },
            ],
        )

        responses.add(
            responses.POST,
            backend.build_url(
                "enrol_manual_enrol_users"
                if enrollment.is_active
                else "enrol_manual_unenrol_users"
            ),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": "2",
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        order.flow.cancel()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.state, "set")

        self.assertEqual(len(responses.calls), 4)

    def test_flows_order_cancel_certificate_product_enrollment_state_failed(self):
        """
        Test that the source enrollment state switches to "failed" if the order is canceled and
        something wrong happens during synchronization of the enrollment mode. Indeed, it
        should try to set it to "honor" when the related order is canceled...
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type="certificate")
        enrollment = factories.EnrollmentFactory(
            course_run__course=course,
            course_run__is_listed=True,
            course_run__state=CourseState.FUTURE_OPEN,
            is_active=True,
        )
        order = factories.OrderFactory(
            course=None,
            product=product,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
        )

        def enrollment_error(*args, **kwargs):
            raise exceptions.EnrollmentError()

        with mock.patch.object(
            DummyLMSBackend, "set_enrollment", side_effect=enrollment_error
        ):
            order.flow.cancel()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.state, "failed")

    def test_flows_order_complete_all_paid(self):
        """
        Test that the complete transition is successful when all installments are paid
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
            ],
        )

        order.flow.complete()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flows_order_failed_payment_to_complete(self):
        """
        Test that the complete transition sets complete state
        when all installments are paid and source state is "failed payment".
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_FAILED_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
            ],
        )

        order.flow.complete()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flows_order_complete_first_paid(self):
        """
        Test that the pending_payment transition failed when the first installment
        is not paid.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_flows_order_pending_payment_failed_with_unpaid_first_installment(self):
        """
        Test that the complete transition sets pending_payment state
        when installments are left to be paid
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.assertRaises(TransitionNotAllowed):
            order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    def test_flows_order_complete_first_payment_failed(self):
        """
        Test that the complete transition sets no_payment state
        when first installment is refused.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.no_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_NO_PAYMENT)

    def test_flows_order_complete_middle_paid(self):
        """
        Test that the complete transition sets pending_payment state
        when installments are left to be paid
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_flows_order_complete_middle_payment_failed(self):
        """
        Test that the complete transition sets failed_payment state
        when an installment but the first one is refused.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.failed_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_FAILED_PAYMENT)

    def test_flows_order_no_payment_to_pending_payment(self):
        """
        Test that the pending payment transition sets pending payment state
        when the first installment is paid and source state is "no payment".
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_NO_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_flows_order_failed_payment_to_pending_payment(self):
        """
        Test that the pending payment transition sets pending payment state
        when an installment is paid and source state is "failed payment".
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_FAILED_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_flows_order_update_not_free_no_card_with_contract(self):
        """
        Test that the order state is set to `to_sign`
        when the order is not free, owner has no card and the order has a contract.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED,
            credit_card=None,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        factories.ContractFactory(
            order=order,
            definition=factories.ContractDefinitionFactory(),
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SIGN)

    def test_flows_order_update_not_free_no_card_no_contract(self):
        """
        Test that the order state is set to `to_save_payment_method` when the order is not free,
        owner has no card and the order has no contract.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED,
            credit_card=None,
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)

    def test_flows_order_update_not_free_with_card_no_contract(self):
        """
        Test that the order state is set to `pending` when the order is not free,
        owner has a card and the order has no contract.
        """
        credit_card = CreditCardFactory(
            initial_issuer_transaction_identifier="4575676657929351"
        )
        run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED,
            owner=credit_card.owner,
            product__target_courses=[run.course],
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    def test_flows_order_update_not_free_with_card_with_contract(self):
        """
        Test that the order state is set to `to_sign` when the order is not free,
        owner has a card and the order has a contract.
        """
        order = factories.OrderFactory(state=enums.ORDER_STATE_ASSIGNED)
        factories.ContractFactory(
            order=order,
            definition=factories.ContractDefinitionFactory(),
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SIGN)

    def test_flows_order_update_from_no_payment_to_completed(self):
        """
        Test that the order state is set to completed when
        the single installment is paid and source state is "no payment".
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_NO_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
            ],
        )

        order.flow.update()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flows_order_update_from_no_payment_to_pending_payment(self):
        """
        Test that the order state is set to pending_payment when
        the first installment is paid and source state is "no payment".
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_NO_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "100.00",
                    "due_date": "2024-01-18",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.update()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_flows_order_update_free_no_contract(self):
        """
        Test that the order state is set to `completed` when the order is free and has no contract.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED,
            product=factories.ProductFactory(price="0.00"),
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flows_order_update_free_with_contract(self):
        """
        Test that the order state is set to `to_sign` when the order is free and has a contract.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED,
            product=factories.ProductFactory(price="0.00"),
        )
        factories.ContractFactory(
            order=order,
            definition=factories.ContractDefinitionFactory(),
        )

        order.flow.update()

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SIGN)

    def test_flows_order_pending(self):
        """
        Test that the pending transition is successful if the order is
        in the ASSIGNED, TO_SIGN_AND_TO_SAVE_PAYMENT_METHOD, TO_SAVE_PAYMENT_METHOD,
        or TO_SIGN state.
        """
        for state in [
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            enums.ORDER_STATE_SIGNING,
        ]:
            with self.subTest(state=state):
                run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
                order = factories.OrderFactory(
                    state=state, product__target_courses=[run.course]
                )
                order.flow.pending()
                self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    def test_flows_order_update(self):
        """
        Test that updating flow is transitioning as expected for all states.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(state=state)
                order.flow.update()
                if state == enums.ORDER_STATE_ASSIGNED:
                    self.assertEqual(
                        order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD
                    )
                else:
                    self.assertEqual(order.state, state)

    def test_flows_order_pending_transition_generate_schedule(self):
        """
        Test that a payment schedule is generated when a not free order transitions
        to `pending` state.
        """
        target_courses = factories.CourseFactory.create_batch(
            1,
            course_runs=CourseRunFactory.create_batch(
                1, state=CourseState.ONGOING_OPEN
            ),
        )
        product = factories.ProductFactory(
            price="100.00", target_courses=target_courses
        )
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=CreditCardFactory(),
            product=product,
        )

        self.assertIsNone(order.payment_schedule)

        order.flow.update()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        self.assertIsNotNone(order.payment_schedule)

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_flows_order_save_payment_method_to_pending_mail_sent_confirming_subscription(
        self,
    ):
        """
        Test the post transition success action of an order when the transition
        goes from TO_SAVE_PAYMENT_METHOD to PENDING is successful, it should trigger the
        email confirmation the subscription that is sent to the user.
        """
        for state in [
            enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        ]:
            with self.subTest(state=state):
                user = factories.UserFactory(
                    email="sam@fun-test.fr",
                    language="en-us",
                    first_name="John",
                    last_name="Doe",
                )
                target_courses = factories.CourseFactory.create_batch(
                    1,
                    course_runs=CourseRunFactory.create_batch(
                        1, state=CourseState.ONGOING_OPEN
                    ),
                )
                product = factories.ProductFactory(
                    price="100.00", target_courses=target_courses
                )
                order = factories.OrderFactory(
                    state=state,
                    owner=user,
                    credit_card=CreditCardFactory(),
                    product=product,
                )
                order.flow.pending()
                self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # check email has been sent
        self.assertEqual(len(mail.outbox), 1)

        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], user.email)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Your order has been confirmed.", email_content)
        self.assertIn("Thank you very much for your purchase!", email_content)
        self.assertIn(order.product.title, email_content)
        # check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Subscription confirmed!")
        self.assertIn("Hello", email_content)
        self.assertNotIn("None", email_content)
        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_flows_order_signing_to_pending_mail_sent_confirming_subscription(self):
        """
        Test the post transition success action of an order when the transition
        goes from SIGNING to PENDING is successful, it should trigger the
        email confirmation the subscription that is sent to the user.
        """
        for state in [
            enums.ORDER_STATE_SIGNING,
        ]:
            with self.subTest(state=state):
                user = factories.UserFactory(
                    email="sam@fun-test.fr",
                    language="en-us",
                    first_name="John",
                    last_name="Doe",
                )
                target_courses = factories.CourseFactory.create_batch(
                    1,
                    course_runs=CourseRunFactory.create_batch(
                        1, state=CourseState.ONGOING_OPEN
                    ),
                )
                product = factories.ProductFactory(
                    price="100.00", target_courses=target_courses
                )
                order = factories.OrderFactory(
                    state=state,
                    owner=user,
                    credit_card=CreditCardFactory(),
                    product=product,
                )
                order.flow.pending()
                self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # check email has been sent
        self.assertEqual(len(mail.outbox), 1)

        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], user.email)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Your order has been confirmed.", email_content)
        self.assertIn("Thank you very much for your purchase!", email_content)
        self.assertIn(order.product.title, email_content)
        # check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Subscription confirmed!")
        self.assertIn("Hello", email_content)
        self.assertNotIn("None", email_content)
        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
        },
    )
    @mock.patch.object(
        DummyPaymentBackend,
        "create_zero_click_payment",
        side_effect=DummyPaymentBackend().create_zero_click_payment,
    )
    def test_flows_order_pending_transition_trigger_payment_installment_due_date_is_current_day(
        self, mock_create_zero_click_payment
    ):
        """
        Test that the post transition success action from the state
        `ORDER_STATE_TO_SAVE_PAYMENT_METHOD` to `ORDER_STATE_PENDING` should trigger a payment if
        when the first installment's due date of the payment schedule is on the current day.
        This may happen when the course has already started.
        """
        order = factories.OrderGeneratorFactory(
            owner=factories.UserFactory(),
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            product__price="5.00",
            product__title="Product 1",
            product__target_courses=factories.CourseFactory.create_batch(
                1,
                course_runs=CourseRunFactory.create_batch(
                    1,
                    state=CourseState.ONGOING_OPEN,
                    is_listed=True,
                ),
            ),
        )
        order.payment_schedule[0]["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.payment_schedule[0]["due_date"] = date(2024, 3, 17)
        order.save()
        order.credit_card = CreditCardFactory(owner=order.owner)

        with mock.patch(
            "django.utils.timezone.localdate", return_value=date(2024, 3, 17)
        ):
            order.flow.update()

        mock_create_zero_click_payment.assert_called_once_with(
            order=order,
            credit_card_token=order.credit_card.token,
            installment={
                "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                "amount": Money("1.5"),
                "due_date": date(2024, 3, 17),
                "state": enums.PAYMENT_STATE_PENDING,
            },
        )

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    @mock.patch.object(
        DummyPaymentBackend,
        "create_zero_click_payment",
        side_effect=DummyPaymentBackend().create_zero_click_payment,
    )
    def test_flows_order_pending_transition_should_not_trigger_payment_if_due_date_is_next_day(
        self, mock_create_zero_click_payment
    ):
        """
        Test that the pending transition success from `ORDER_STATE_TO_SAVE_PAYMENT_METHOD` to
        `ORDER_STATE_PENDING` but it does not trigger a payment when the first installment's
        due date is the next day and not on the current day. In our case, the cronjob
        will take care to process the upcoming payment the following day, so the order must be
        in 'pending' state at the end.
        """
        order = factories.OrderGeneratorFactory(
            owner=factories.UserFactory(),
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            product__title="Product 2",
            product__target_courses=factories.CourseFactory.create_batch(
                1,
                course_runs=CourseRunFactory.create_batch(
                    1,
                    state=CourseState.ONGOING_OPEN,
                    is_listed=True,
                ),
            ),
        )
        order.payment_schedule[0]["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.payment_schedule[0]["due_date"] = date(2024, 3, 18)
        order.save()
        order.credit_card = CreditCardFactory(owner=order.owner)

        with mock.patch(
            "django.utils.timezone.localdate", return_value=date(2024, 3, 17)
        ):
            order.flow.update()

        mock_create_zero_click_payment.assert_not_called()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
        },
    )
    def test_flows_order_canceled_should_be_able_to_be_refund_when_order_is_not_free(
        self,
    ):
        """
        Test that the refund flow method should set an order to state `refund`
        only if the order was in state `canceled` and has at least 1 installment paid.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            product__price=5,
        )
        order.flow.cancel()

        order.flow.refunding()

        self.assertEqual(order.state, enums.ORDER_STATE_REFUNDING)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
        },
    )
    def test_flows_order_canceled_should_stay_canceled_when_the_order_is_free(self):
        """
        Test when a free order is in state `canceled`, it can't go to state `refund`.
        """
        order = factories.OrderGeneratorFactory(
            product__price=0, state=enums.ORDER_STATE_CANCELED
        )

        with self.assertRaises(TransitionNotAllowed):
            order.flow.refunding()

        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_flows_order_refunding_failure_when_state_is_not_canceled(self):
        """
        Test that the refunding flow transition for an order does not work with states other
        than `canceled`.
        """
        order_state_choices = tuple(
            choice
            for choice in enums.ORDER_STATE_CHOICES
            if choice[0]
            not in (
                enums.ORDER_STATE_REFUNDING,
                enums.ORDER_STATE_REFUNDED,
                enums.ORDER_STATE_CANCELED,
            )
        )
        for state, _ in order_state_choices:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(state=state)
                with self.assertRaises(TransitionNotAllowed):
                    order.flow.refunding()
                self.assertEqual(order.state, state)

    def test_flows_order_transition_to_refunded_should_fail_if_source_state_is_not_refunding(
        self,
    ):
        """
        Test that only the transition to `refunded` state is not possible if the order's state
        is not `refunding`.
        """
        order_state_choices = tuple(
            choice
            for choice in enums.ORDER_STATE_CHOICES
            if choice[0] not in (enums.ORDER_STATE_REFUNDING,)
        )
        for state, _ in order_state_choices:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(state=state)
                with self.assertRaises(TransitionNotAllowed):
                    order.flow.refunding()
                self.assertEqual(order.state, state)

    def test_flows_order_transition_to_refunded(self):
        """Test the state `refunding` to transition to `refunded` is successful"""
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_REFUNDING, product__price=10
        )
        order.payment_schedule[0]["state"] = enums.PAYMENT_STATE_REFUNDED
        order.save()

        order.flow.refunded()

        self.assertEqual(order.state, enums.ORDER_STATE_REFUNDED)
