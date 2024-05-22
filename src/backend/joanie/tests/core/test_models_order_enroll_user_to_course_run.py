"""
Test suite the `enroll_user_to_course_run` method on Order model
"""

import random

from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import CourseState, Enrollment
from joanie.payment.factories import BillingAddressDictFactory, InvoiceFactory


# pylint: disable=too-many-public-methods
class EnrollUserToCourseRunOrderModelsTestCase(TestCase):
    """Test suite for `enroll_user_to_course_run` method on the Order model."""

    def _create_validated_order(self, **kwargs):
        order = factories.OrderFactory(**kwargs)
        order.flow.assign()
        order.submit(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(Enrollment.objects.count(), 0)

        # - Create an invoice to mark order as validated
        InvoiceFactory(order=order, total=order.total)

        # - Validate the order should automatically enroll user to course run
        order.flow.validate()

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_models_order_enroll_user_to_course_run_one_open(self):
        """
        If a target course has only one open course run, the enrollment should be automatic.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        factories.CourseRunFactory(
            course=target_course,
            state=random.choice(
                [
                    CourseState.ONGOING_OPEN,
                    CourseState.FUTURE_OPEN,
                    CourseState.ARCHIVED_OPEN,
                ]
            ),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_models_order_enroll_user_to_course_run_one_closed(self):
        """
        If a target course has only one course run. The enrollment should not be automatic if
        this course run is closed.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        factories.CourseRunFactory(
            course=target_course,
            state=random.choice(
                [
                    CourseState.FUTURE_NOT_YET_OPEN,
                    CourseState.FUTURE_CLOSED,
                    CourseState.ONGOING_CLOSED,
                    CourseState.ARCHIVED_CLOSED,
                    CourseState.TO_BE_SCHEDULED,
                ]
            ),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertFalse(Enrollment.objects.exists())

    def test_models_order_enroll_user_to_course_run_several_open(self):
        """
        If a target course has several open course runs, the enrollment should not be automatic.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        for _i in range(3):
            factories.CourseRunFactory(
                course=target_course,
                state=random.choice(
                    [
                        CourseState.ONGOING_OPEN,
                        CourseState.FUTURE_OPEN,
                        CourseState.ARCHIVED_OPEN,
                    ]
                ),
            )

        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertFalse(Enrollment.objects.exists())

    def test_models_order_enroll_user_to_course_run_specific_open(self):
        """
        If a target course has several open course runs but only one of them is specifically
        linked to the target course, the enrollment should be automatic because enrollment is
        possible only on this course run.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        # - Link 2 course runs to the target_course
        course_run, *_other_course_runs = factories.CourseRunFactory.create_batch(
            3,
            course=target_course,
            state=random.choice(
                [
                    CourseState.ONGOING_OPEN,
                    CourseState.FUTURE_OPEN,
                    CourseState.ARCHIVED_OPEN,
                ]
            ),
        )

        # - Only one of the course runs is specifically targeted
        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[course_run]
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_models_order_enroll_user_to_course_run_several_but_one_open(self):
        """
        If a target course has several course runs but only one of them is open, the enrollment
        should be automatic because enrollment is possible only on this course run.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        # - Link several course runs to the target_course, but only one is open
        factories.CourseRunFactory(
            course=target_course,
            state=random.choice(
                [
                    CourseState.ONGOING_OPEN,
                    CourseState.FUTURE_OPEN,
                    CourseState.ARCHIVED_OPEN,
                ]
            ),
        )
        for state in [
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_CLOSED,
            CourseState.ONGOING_CLOSED,
            CourseState.ARCHIVED_CLOSED,
            CourseState.TO_BE_SCHEDULED,
        ]:
            factories.CourseRunFactory(course=target_course, state=state)

        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_models_order_enroll_user_to_course_run_specific_closed_other_open(self):
        """
        If a target course has an open course run and a closed course run specifically
        linked to it, validating the order should not enroll to the open course run.
        """
        [course, target_course] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=[course])

        # - Link several course runs to the target_course, but only one is open
        factories.CourseRunFactory(
            course=target_course,
            state=random.choice(
                [
                    CourseState.ONGOING_OPEN,
                    CourseState.FUTURE_OPEN,
                    CourseState.ARCHIVED_OPEN,
                ]
            ),
        )
        closed_course_run = factories.CourseRunFactory(
            course=target_course,
            state=random.choice(
                [
                    CourseState.FUTURE_NOT_YET_OPEN,
                    CourseState.FUTURE_CLOSED,
                    CourseState.ONGOING_CLOSED,
                    CourseState.ARCHIVED_CLOSED,
                    CourseState.TO_BE_SCHEDULED,
                ]
            ),
        )

        factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[closed_course_run]
        )

        self._create_validated_order(
            product=product,
            course=course,
        )

        self.assertEqual(Enrollment.objects.count(), 0)
