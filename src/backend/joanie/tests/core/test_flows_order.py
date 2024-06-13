"""
Test suite for order flows.
"""

# pylint: disable=too-many-lines,too-many-public-methods
import json
from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.test.utils import override_settings

import responses
from viewflow.fsm import TransitionNotAllowed

from joanie.core import enums, exceptions, factories
from joanie.core.models import CourseState, Enrollment
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.dummy import DummyLMSBackend
from joanie.payment.factories import (
    BillingAddressDictFactory,
    CreditCardFactory,
    InvoiceFactory,
)
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

        order.flow.init(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)

    def test_flow_order_assign_free_product(self):
        """
        It should set the order state to ORDER_STATE_COMPLETED
        when the order has a free product.
        """
        order = factories.OrderFactory(product__price=0)

        order.flow.init()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flow_order_assign_no_billing_address(self):
        """
        It should raise a TransitionNotAllowed exception
        when the order has no billing address and the order is not free.
        """
        order = factories.OrderFactory()

        with self.assertRaises(TransitionNotAllowed):
            order.flow.init()

        self.assertEqual(order.state, enums.ORDER_STATE_ASSIGNED)

    def test_flow_order_assign_no_organization(self):
        """
        It should raise a TransitionNotAllowed exception
        when the order has no organization.
        """
        order = factories.OrderFactory(organization=None)

        with self.assertRaises(TransitionNotAllowed):
            order.flow.init()

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
        order.flow.init()

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
        order.flow.init()
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )
        InvoiceFactory(order=order_invoice)
        self.assertEqual(order_invoice.flow._can_be_state_completed(), True)  # pylint: disable=protected-access
        order_invoice.flow.complete()
        self.assertEqual(order_invoice.state, enums.ORDER_STATE_COMPLETED)

        order_free = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=enums.ORDER_STATE_DRAFT,
        )
        order_free.flow.init()

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
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.OK,
            json={"is_active": True},
        )

        # Create an order
        order = factories.OrderFactory(product=product)
        order.flow.init()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        enrollment = Enrollment.objects.get(
            user=order.owner, course_run__resource_link=resource_link
        )
        self.assertEqual(enrollment.state, "set")
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": "verified",
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
    def test_flows_order_validate_auto_enroll_failure(self):
        """
        When an order is validated, if one target course contains only one course run
        and this one is opened for enrollment, the user should be automatically enrolled
        If the enrollment request fails, the order should be validated.
        """
        course = factories.CourseFactory()
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        factories.CourseRunFactory(
            course=course,
            resource_link=resource_link,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=HTTPStatus.BAD_REQUEST,
            json=None,
        )

        # Create an order
        order = factories.OrderFactory(product=product)
        order.flow.init()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        enrollment = Enrollment.objects.get(
            user=order.owner, course_run__resource_link=resource_link
        )
        self.assertEqual(enrollment.state, "failed")
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": "verified",
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
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
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
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(product=product, owner=enrollment.user)
        order.flow.init()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[1].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": "verified",
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

        order.flow.init()

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
        order.flow.init()

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

        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        enrollment = factories.EnrollmentFactory(
            course_run__course=course,
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__resource_link=resource_link,
        )
        order = factories.OrderFactory(
            course=None,
            product=product,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
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

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": "honor",
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

        self.assertEqual(enrollment.state, "failed")
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
            ],
        )

        order.flow.complete()

        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

    def test_flows_order_complete_first_paid(self):
        """
        Test that the complete transition sets pending_payment state
        when installments are left to be paid
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.flow.pending_payment()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
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
                    "due_date": "2024-01-17T00:00:00+00:00",
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
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_ASSIGNED, owner=credit_card.owner
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
            enums.ORDER_STATE_TO_SIGN,
        ]:
            with self.subTest(state=state):
                order = factories.OrderFactory(state=state)
                order.flow.pending()
                self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
