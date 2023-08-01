"""Test suite for the CourseRunFactory."""
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
        If developer provides dates and state to generate a CourseRun, dates should
        have priority over state.
        """

        start = timezone.now() + timedelta(days=1)

        course_run = CourseRunFactory(state=CourseState.ONGOING_OPEN, start=start)
        self.assertEqual(course_run.state["priority"], CourseState.FUTURE_OPEN)
        self.assertEqual(course_run.start, start)
