"""Test suite for the CourseRunFactory."""

import random
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from joanie.core.factories import CourseRunFactory
from joanie.core.models import CourseState


class TestCourseRunFactory(TestCase):
    """Test suite for the CourseRunFactory."""

    def test_factory_course_run_generate_with_state(self):
        """
        CourseRunFactory should take a `state` param and
        generate a course run with dates corresponding to the provided state.
        """
        for state in [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_CLOSED,
            CourseState.ONGOING_CLOSED,
            CourseState.ARCHIVED_CLOSED,
            CourseState.TO_BE_SCHEDULED,
        ]:
            course_run = CourseRunFactory(state=state)
            self.assertEqual(course_run.state["priority"], state)

    def test_factory_course_run_generate_with_state_and_dates(self):
        """
        If developer provides dates and state to generate a CourseRun,
        dates should have priority over state.
        """
        start = timezone.now() - timedelta(days=1)

        course_run = CourseRunFactory(state=CourseState.FUTURE_OPEN, start=start)
        self.assertEqual(course_run.start, start)

    def test_factory_course_run_archived_with_invalid_start_date(self):
        """
        Trying to create an archived course run with a start date greater than
        ref date should raise a ValueError.
        """
        start = timezone.now() + timedelta(days=1)

        with self.assertRaises(ValueError) as context:
            CourseRunFactory(
                state=random.choice(
                    [CourseState.ARCHIVED_CLOSED, CourseState.ARCHIVED_OPEN]
                ),
                start=start,
            )

        self.assertEqual(
            str(context.exception), "Start date must be less than ref date."
        )

    def test_factory_course_run_future_not_yet_opened_with_invalid_start_date(self):
        """
        Trying to create a future not yet opened course run with a start date less than
        ref date should raise a ValueError.
        """
        start = timezone.now() - timedelta(days=2)

        with self.assertRaises(ValueError) as context:
            CourseRunFactory(state=CourseState.FUTURE_NOT_YET_OPEN, start=start)

        self.assertEqual(
            str(context.exception), "Start date must be greater than ref date."
        )

    def test_factory_course_run_future_not_yet_opened_with_invalid_end_date(self):
        """
        Trying to create a future not yet opened course run with an end date less than
        ref date should raise a Value Error as the enrollment start date will be greater
        than the end date.
        """
        end = timezone.now() - timedelta(days=2)

        with self.assertRaises(ValueError) as context:
            CourseRunFactory(state=CourseState.FUTURE_NOT_YET_OPEN, end=end)

        self.assertEqual(
            str(context.exception),
            "End date must be greater than enrollment start date.",
        )

    def test_factory_course_run_not_archived_open_with_invalid_end_date(self):
        """
        Trying to create a course run ongoing or future opnened for enrollment with an
        end date less than ref date should raise a Value Error.
        """
        end = timezone.now() - timedelta(days=2)

        with self.assertRaises(ValueError) as context:
            CourseRunFactory(
                state=random.choice(
                    [CourseState.ONGOING_OPEN, CourseState.FUTURE_OPEN]
                ),
                end=end,
            )

        self.assertEqual(
            str(context.exception), "End date must be greater than ref date."
        )
