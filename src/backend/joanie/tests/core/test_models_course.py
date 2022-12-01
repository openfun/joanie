"""
Test suite for course models
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from joanie.core import factories, models
from joanie.core.factories import CourseFactory, CourseRunFactory
from joanie.core.models import CourseState


class CourseModelsTestCase(TestCase):
    """Test suite for the Course model."""

    def test_models_course_fields_code_normalize(self):
        """The `code` field should be normalized to an ascii slug on save."""
        course = factories.CourseFactory()

        course.code = "Là&ça boô"
        course.save()
        self.assertEqual(course.code, "LACA-BOO")

    def test_models_course_fields_code_unique(self):
        """The `code` field should be unique among courses."""
        factories.CourseFactory(code="the-unique-code")

        # Creating a second course with the same code should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.CourseFactory(code="the-unique-code")

        self.assertEqual(
            context.exception.messages[0], "Course with this Code already exists."
        )
        self.assertEqual(
            models.Course.objects.filter(code="THE-UNIQUE-CODE").count(), 1
        )


class CourseStateModelsTestCase(TestCase):
    """
    Unit test suite for computing a date to display on the course glimpse depending on the state
    of its related course runs:
        0: a run is ongoing and open for enrollment > "closing on": {enrollment_end}
        1: a run is future and open for enrollment > "starting on": {start}
        2: a run is future and not yet open or already closed for enrollment >
        "starting on": {start}
        3: a run is ongoing but closed for enrollment > "on going": {None}
        4: there's a finished run in the past > "archived": {None}
        5: there are no runs at all > "coming soon": {None}
    """

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def create_run_ongoing_open(self, course):
        """Create an ongoing course run that is open for enrollment."""
        return CourseRunFactory(
            course=course,
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
        )

    def create_run_ongoing_closed(self, course):
        """Create an ongoing course run that is closed for enrollment."""
        return CourseRunFactory(
            course=course,
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=1),
            enrollment_end=self.now,
        )

    def create_run_archived_open(self, course):
        """Create an archived course run."""
        return CourseRunFactory(
            course=course,
            start=self.now - timedelta(hours=1),
            end=self.now,
            enrollment_end=self.now + timedelta(hours=1),
        )

    def create_run_archived_closed(self, course):
        """Create an archived course run."""
        return CourseRunFactory(
            course=course,
            start=self.now - timedelta(hours=1),
            end=self.now,
            enrollment_end=self.now - timedelta(hours=1),
        )

    def create_run_future_not_yet_open(self, course):
        """Create a course run in the future and not yet open for enrollment."""
        return CourseRunFactory(
            course=course,
            start=self.now + timedelta(hours=2),
            enrollment_start=self.now + timedelta(hours=1),
        )

    def create_run_future_closed(self, course):
        """Create a course run in the future and already closed for enrollment."""
        return CourseRunFactory(
            course=course,
            start=self.now + timedelta(hours=1),
            enrollment_start=self.now - timedelta(hours=2),
            enrollment_end=self.now - timedelta(hours=1),
        )

    def create_run_future_open(self, course):
        """Create a course run in the future and open for enrollment."""
        return CourseRunFactory(
            course=course,
            start=self.now + timedelta(hours=1),
            enrollment_start=self.now - timedelta(hours=1),
            enrollment_end=self.now + timedelta(hours=1),
        )

    def test_models_course_state_to_be_scheduled(self):
        """
        Confirm course state result when there is no course runs at all.
        """
        course = CourseFactory()
        with self.assertNumQueries(1):
            state = course.state
        self.assertEqual(state, CourseState(7))

    def test_models_course_state_archived_closed(self):
        """
        Confirm course state when there is a course run only in the past.
        """
        course = CourseFactory()
        self.create_run_archived_closed(course)
        with self.assertNumQueries(3):
            state = course.state
        self.assertEqual(state, CourseState(6))

    def test_models_course_state_archived_open(self):
        """
        Confirm course state when there is a past course run but open for enrollment.
        """
        course = CourseFactory()
        course_run = self.create_run_archived_open(course)
        with self.assertNumQueries(3):
            state = course.state
        self.assertEqual(state, CourseState(2, course_run.enrollment_end))

    def test_models_course_state_ongoing_enrollment_closed(self):
        """
        Confirm course state when there is an ongoing course run but closed for
        enrollment.
        """
        course = CourseFactory()
        self.create_run_ongoing_closed(course)
        with self.assertNumQueries(3):
            state = course.state
        self.assertEqual(state, CourseState(5))

    def test_models_course_state_future_enrollment_not_yet_open(self):
        """
        Confirm course state when there is a future course run but not yet open for
        enrollment.
        """
        course = CourseFactory()
        course_run = self.create_run_future_not_yet_open(course)
        with self.assertNumQueries(3):
            state = course.state
        expected_state = CourseState(3, course_run.start)
        self.assertEqual(state, expected_state)

    def test_models_course_state_future_enrollment_closed(self):
        """
        Confirm course state when there is a future course run but closed for
        enrollment.
        """
        course = CourseFactory()
        self.create_run_future_closed(course)
        with self.assertNumQueries(3):
            state = course.state
        expected_state = CourseState(4)
        self.assertEqual(state, expected_state)

    def test_models_course_state_future_enrollment_open(self):
        """
        Confirm course state when there is a future course run open for enrollment.
        """
        course = CourseFactory()
        course_run = self.create_run_future_open(course)
        with self.assertNumQueries(3):
            state = course.state
        expected_state = CourseState(1, course_run.start)
        self.assertEqual(state, expected_state)

    def test_models_course_state_ongoing_open(self):
        """
        Confirm course state when there is an ongoing course run open for enrollment.
        """
        course = CourseFactory()
        course_run = self.create_run_ongoing_open(course)
        with self.assertNumQueries(3):
            state = course.state
        expected_state = CourseState(0, course_run.enrollment_end)
        self.assertEqual(state, expected_state)
