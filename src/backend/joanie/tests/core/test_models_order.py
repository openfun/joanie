"""
Test suite for order models
"""
import json
import random
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

import responses
from django_fsm import TransitionNotAllowed

from joanie.core import enums, exceptions, factories
from joanie.core.models import CourseState, Enrollment
from joanie.lms_handler.backends.dummy import DummyLMSBackend
from joanie.payment.factories import BillingAddressDictFactory, InvoiceFactory


# pylint: disable=too-many-public-methods
class OrderModelsTestCase(TestCase):
    """Test suite for the Order model."""

    def test_models_order_enrollment_was_created_by_order(self):
        """
        The enrollment linked to an order, must not orginated from an order.
        This is because, being flagged with "was_created_by_order" as True, this enrollment will
        not be listed directly on the student dashboard. It will be visible only behind one of
        the orders listed on the dashboard.
        """
        course_run = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
            is_listed=True,
        )
        factories.ProductFactory(target_courses=[course_run.course], type="enrollment")
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, was_created_by_order=True
        )

        certificate_product = factories.ProductFactory(
            courses=[course_run.course], type="certificate"
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=certificate_product, course=None, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': [\"Orders can't be placed on enrollments originating "
                'from an order."]}'
            ),
        )

    def test_models_order_enrollment_owned_by_enrollment_user(self):
        """The enrollment linked to an order, must belong to the order owner."""
        course_run = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run)

        certificate_product = factories.ProductFactory(
            courses=[course_run.course], type="certificate"
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                # Forcing the user to something else than the enrollment user
                owner=factories.UserFactory(),
                product=certificate_product,
                course=None,
                enrollment=enrollment,
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['The enrollment should belong to the owner of this order.']}"
            ),
        )

    def test_models_order_course_enrollment_constraint_product_certificate(self):
        """
        Orders for "certificate" type products can only be linked to an enrollment.
        The course field must remain null.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type="certificate")
        organization = product.course_relations.get().organizations.first()
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN, course_run__is_listed=True
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=product, course=course, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            "{'course': ['course field should be left empty for certificate products.']}",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization, product=product, course=None, enrollment=None
            )
        self.assertEqual(
            str(context.exception),
            "{'enrollment': ['enrollment field should be set for certificate products.']}",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(product=product, course=course, enrollment=None)
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['enrollment field should be set for certificate products.'], "
                "'course': ['course field should be left empty for certificate products.']}"
            ),
        )

        factories.OrderFactory(
            organization=organization,
            product=product,
            course=None,
            enrollment=enrollment,
        )

    def _enrollment_constraint_product_on_courses(self, product_type):
        """
        Factorized test code to test "course" and "enrollment" fields for
        products that are sold on the syllabus.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type=product_type)
        organization = product.course_relations.get().organizations.first()
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN, course_run__is_listed=True
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=product, course=course, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['enrollment field should be left empty "
                f"for {product_type} products.']}}"
            ),
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization, product=product, course=None, enrollment=None
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'course': ['course field should be set "
                f"for {product_type} products.']}}"
            ),
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization,
                product=product,
                course=None,
                enrollment=enrollment,
            )
        self.assertEqual(
            str(context.exception),
            (
                f"{{'course': ['course field should be set for {product_type} products.'], "
                "'enrollment': ['enrollment field should be left empty "
                f"for {product_type} products.']}}"
            ),
        )

        factories.OrderFactory(
            product=product,
            course=course,
            enrollment=None,
        )

    def test_models_order_course_enrollment_constraint_product_credential(self):
        """
        Orders for "credential" type products can only be linked to a course.
        The enrollment field must remain null.
        """
        self._enrollment_constraint_product_on_courses("credential")

    def test_models_order_course_enrollment_constraint_product_enrollment(self):
        """
        Orders for "enrollment" type products can only be linked to a course.
        The enrollment field must remain null.
        """
        self._enrollment_constraint_product_on_courses("enrollment")

    def test_models_order_course_owner_product_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same course,
        product and owner fields that are not canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product)

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                owner=order.owner,
                product=product,
                course=course,
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['"
                "An order for this product and course already exists."
                "']}"
            ),
        )

    @staticmethod
    def test_models_order_course_owner_product_unique_canceled():
        """
        Canceled orders are not taken into account for uniqueness on the course, product and
        owner triplet.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_CANCELED
        )

        factories.OrderFactory(owner=order.owner, product=product, course=order.course)

    def test_models_order_course_runs_relation_sorted_by_position(self):
        """The product/course relation should be sorted by position."""
        courses = factories.CourseFactory.create_batch(5)
        product = factories.ProductFactory(target_courses=courses)

        # Create an order link to the product
        order = factories.OrderFactory(product=product)
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        target_courses = order.target_courses.order_by("product_target_relations")
        self.assertCountEqual(target_courses, courses)

        position = 0
        for target_course in target_courses:
            course_position = target_course.product_target_relations.get().position
            self.assertGreaterEqual(course_position, position)
            position = course_position

    def test_models_order_course_in_product_new(self):
        """
        An order's course should be included in the target courses of its related product at
        the moment the order is created.
        """
        course = factories.CourseFactory()
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(title="Traçabilité")
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )
        self.assertTrue(product.courses.filter(id=course.id).exists())

        other_course = factories.CourseFactory(title="Mathématiques")

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                course=other_course, product=product, organization=organization
            )

        self.assertEqual(
            context.exception.messages,
            [
                'The course "Mathématiques" and the product "Traçabilité" '
                'should be linked for organization "fun".'
            ],
        )

    @staticmethod
    def test_models_order_course_in_product_existing():
        """
        An order's course can be absent from the related product target courses when updating an
        existing order.
        """
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=courses)
        order = factories.OrderFactory(product=product)
        order.course = factories.CourseFactory()
        order.save()

    def test_models_order_state_property(self):
        """
        Order state property is set and related with invoice.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(title="Traçabilité", courses=[course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_SUBMITTED
        )

        # 2 - When an invoice is linked to the order, and the method validate() is
        # called its state is `validated`
        InvoiceFactory(order=order, total=order.total)
        order.validate()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        # 3 - When order is canceled, its state is `canceled`
        order.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_models_order_state_property_validated_when_free(self):
        """
        When an order relies on a free product, its state should be automatically
        validated without any invoice and without calling the validate()
        method.
        """
        courses = factories.CourseFactory.create_batch(2)
        # Create a free product
        product = factories.ProductFactory(courses=courses, price=0)
        order = factories.OrderFactory(product=product, total=0.00)
        order.submit()

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_models_order_validate(self):
        """
        Order has a validate method which is in charge to enroll owner to courses
        with only one course run if order state is equal to validated.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        # - Link only one course run to target_course
        factories.CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
        )

        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course]
        )

        order = factories.OrderFactory(
            owner=owner,
            product=product,
            course=course,
        )
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(Enrollment.objects.count(), 0)

        # - Create an invoice to mark order as validated
        InvoiceFactory(order=order, total=order.total)

        # - Validate the order should automatically enroll user to course run
        with self.assertNumQueries(21):
            order.validate()

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_models_order_validate_with_inactive_enrollment(self):
        """
        Order has a validate method which is in charge to enroll owner to courses
        with only one course run if order state is equal to validated. If the user has
        already an inactive enrollment, it should be activated.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        # - Link only one course run to target_course
        course_run = factories.CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )

        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course]
        )

        order = factories.OrderFactory(
            owner=owner,
            product=product,
            course=course,
        )
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        # - Create an inactive enrollment for related course run
        enrollment = factories.EnrollmentFactory(
            user=owner, course_run=course_run, is_active=False
        )

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(Enrollment.objects.count(), 1)

        # - Create an invoice to mark order as validated
        InvoiceFactory(order=order, total=order.total)

        # - Validate the order should automatically enroll user to course run
        with self.assertNumQueries(27):
            order.validate()

        enrollment.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(enrollment.is_active, True)

    def test_models_order_cancel(self):
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
        order.submit()

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(
            course_run=cr1, user=owner, is_active=True, was_created_by_order=True
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should be unenrolled to related enrollments
        order.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=False).count(), 1)

    def test_models_order_cancel_with_course_implied_in_several_products(self):
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
        order.submit()
        factories.OrderFactory(owner=owner, product=product_2, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(
            course_run=cr1, user=owner, is_active=True, was_created_by_order=True
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should not be unenrolled to related enrollments
        with self.assertNumQueries(12):
            order.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_models_order_cancel_with_listed_course_run(self):
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
            order.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_models_order_get_enrollments(self):
        """
        Order model implements a `get_enrollment` method to retrieve enrollments
        related to the order instance.
        """
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(
            price="0.00", target_courses=[cr1.course, cr2.course]
        )
        order = factories.OrderFactory(product=product)
        order.submit()

        # - As the two product's target courses have only one course run, order owner
        #   should have been automatically enrolled to those course runs.
        with self.assertNumQueries(1):
            self.assertEqual(len(order.get_target_enrollments()), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=True)), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=False)), 0)

        # - Then order is canceled so user should be unenrolled to course runs.
        order.cancel()
        self.assertEqual(len(order.get_target_enrollments()), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=True)), 0)
        self.assertEqual(len(order.get_target_enrollments(is_active=False)), 2)

    def test_models_order_target_course_runs_property(self):
        """
        Order model has a target course runs property to retrieve all course runs
        related to the order instance.
        """
        [course1, course2] = factories.CourseFactory.create_batch(2)
        [cr1, cr2] = factories.CourseRunFactory.create_batch(2, course=course1)
        [cr3, cr4] = factories.CourseRunFactory.create_batch(2, course=course2)
        product = factories.ProductFactory(target_courses=[course1, course2])

        # - Link cr3 to the product course relations
        relation = product.target_course_relations.get(course=course2)
        relation.course_runs.add(cr3)

        # - Create an order link to the product
        order = factories.OrderFactory(product=product)
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        # - Update product course relation, order course relation should not be impacted
        relation.course_runs.set([])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - product.target_course_runs should return all course runs
            course_runs = product.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 4)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3, cr4])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - order.target_course_runs should only return cr1, cr2, cr3
            course_runs = order.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 3)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3])

    def test_models_order_validate_transition(self):
        """
        Test that the validate transition is successful
        when the order is free or has invoices and is in the
        ORDER_STATE_PENDING state
        """
        order_invoice = factories.OrderFactory(
            product=factories.ProductFactory(price="10.00"),
            state=enums.ORDER_STATE_SUBMITTED,
        )
        InvoiceFactory(order=order_invoice)
        self.assertEqual(order_invoice.can_be_state_validated(), True)
        order_invoice.validate()
        self.assertEqual(order_invoice.state, enums.ORDER_STATE_VALIDATED)

        order_free = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=enums.ORDER_STATE_DRAFT,
        )
        order_free.submit()
        self.assertEqual(order_free.can_be_state_validated(), True)
        # order free are automatically validated without calling the validate method
        # but submit need to be called nonetheless
        self.assertEqual(order_free.state, enums.ORDER_STATE_VALIDATED)
        with self.assertRaises(TransitionNotAllowed):
            order_free.validate()

    def test_models_order_validate_transition_failure(self):
        """
        Test that the validate transition fails when the
        order is not free and has no invoices
        """
        order_no_invoice = factories.OrderFactory(
            product=factories.ProductFactory(price="10.00"),
            state=enums.ORDER_STATE_PENDING,
        )
        self.assertEqual(order_no_invoice.can_be_state_validated(), False)
        with self.assertRaises(TransitionNotAllowed):
            order_no_invoice.validate()
        self.assertEqual(order_no_invoice.state, enums.ORDER_STATE_PENDING)

    def test_models_order_transition_failure_when_not_pending(self):
        """Test that the validate transition fails when the
        order is not in the ORDER_STATE_PENDING state
        """
        order = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=enums.ORDER_STATE_VALIDATED,
        )
        self.assertEqual(order.can_be_state_validated(), True)
        with self.assertRaises(TransitionNotAllowed):
            order.validate()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    @responses.activate
    def test_models_order_validate_preexisting_enrollments_targeted(self):
        """
        When an order is validated, if the user was previously enrolled for free in any of the
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

        # Create a pre-existing free enrollment
        enrollment = factories.EnrollmentFactory(course_run=course_run)
        order = factories.OrderFactory(product=product)

        url = "http://openedx.test/api/enrollment/v1/enrollment"

        responses.add(
            responses.POST,
            url,
            status=200,
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
            order.submit()

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": enrollment.is_active,
                "mode": "verified",
                "user": enrollment.user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    def test_models_order_cancel_success(self):
        """Test that the cancel transition is successful from any state"""

        order = factories.OrderFactory(
            product=factories.ProductFactory(price="0.00"),
            state=random.choice(enums.ORDER_STATE_CHOICES)[0],
        )
        order.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    @responses.activate
    def test_models_order_cancel_certificate_product_openedx_enrollment_mode(self):
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
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__resource_link=resource_link,
        )
        order = factories.OrderFactory(
            course=None,
            product=product,
            enrollment=enrollment,
            state="validated",
        )

        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=200,
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
            order.cancel()

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

    def test_models_order_create_target_course_relations_on_submit(self):
        """
        When an order is submitted, product target courses should be copied to the order
        """
        product = factories.ProductFactory(
            target_courses=factories.CourseFactory.create_batch(2)
        )
        order = factories.OrderFactory(product=product)

        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)
        self.assertEqual(order.target_courses.count(), 0)

        # Then we submit the order
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), 2)

    def test_models_order_dont_create_target_course_relations_on_resubmit(self):
        """
        When an order is submitted again, product target courses should not be copied
        again to the order
        """
        product = factories.ProductFactory(
            target_courses=factories.CourseFactory.create_batch(2)
        )
        order = factories.OrderFactory(product=product)

        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)
        self.assertEqual(order.target_courses.count(), 0)

        # Then we submit the order
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), 2)

        # Unfortunately, order transitions to pending state
        order.pending()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # So we need to submit it again
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), product.target_courses.count())
