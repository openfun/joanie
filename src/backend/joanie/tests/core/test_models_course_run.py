"""
Test suite for order models
"""
import random
from datetime import datetime, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone as django_timezone

from joanie.core import factories
from joanie.core.factories import CourseRunFactory

# pylint: disable=too-many-public-methods


class CourseRunModelsTestCase(TestCase):
    """Test suite for the CourseRun model."""

    def setUp(self):
        super().setUp()
        self.now = django_timezone.now()

    def test_models_course_run_normalized(self):
        """
        The resource_link field should be normalized on save.
        """
        course_run = factories.CourseRunFactory()
        course_run.resource_link = "https://www.Example.Com:443/Capitalized-Path"
        course_run.save()
        self.assertEqual(
            course_run.resource_link, "https://www.example.com/Capitalized-Path"
        )

    def test_models_course_run_dates_not_required(self):
        """
        Course run dates are not required.
        """
        course_run = factories.CourseRunFactory(
            start=None, end=None, enrollment_start=None, enrollment_end=None
        )
        for field in ["start", "end", "enrollment_start", "enrollment_end"]:
            self.assertIsNone(getattr(course_run, field))

    def test_models_course_run_unique(self):
        """The resource link field should be unique."""
        course_run = factories.CourseRunFactory()

        with self.assertRaises(ValidationError) as context:
            factories.CourseRunFactory(resource_link=course_run.resource_link)

        self.assertEqual(
            "{'resource_link': ['Course run with this Resource link already exists.']}",
            str(context.exception),
        )

    def test_models_course_run_state_start_to_be_scheduled(self):
        """
        A course run that has no start date should return a state with priority 6
        and "to be scheduled" as text.
        """
        course_run = CourseRunFactory(start=None)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 7,
                "text": "to be scheduled",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_enrollment_start_to_be_scheduled(self):
        """
        A course run that has no enrollment start date should return a state with priority 6
        and "to be scheduled" as text.
        """
        course_run = CourseRunFactory(enrollment_start=None)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 7,
                "text": "to be scheduled",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_no_end_date(self):
        """
        A course run with no end date is deemed to be forever on-going.
        """
        course_run = CourseRunFactory(end=None)

        # The course run should be open during its enrollment period
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.enrollment_end.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertIn(dict(state)["priority"], [0, 1])

        # The course run should be on-going at any date after its end of enrollment
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_end.timestamp()),
                int(datetime(9999, 12, 31).timestamp()),
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 5,
                "text": "on-going",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_no_enrollment_end(self):
        """
        A course run that has no end of enrollment is deemed to be always open.
        """
        course_run = CourseRunFactory(enrollment_end=None)

        # The course run should be open between its start of enrollment and its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.start.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": course_run.start,
            },
        )

        # The course run should be on-going & open between its start and its end
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.start.timestamp()) + 1,
                int(course_run.end.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 0,
                "text": "forever open",
                "call_to_action": "enroll now",
                "datetime": None,
            },
        )

        # The course run should be archived open after its end
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.end.timestamp()) + 1,
                int(datetime(9999, 12, 31).timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 2,
                "text": "forever open",
                "call_to_action": "study now",
                "datetime": None,
            },
        )

    def test_models_course_run_state_forever_open(self):
        """
        A course run that has no end of enrollement and no end should be forever open.
        """
        course_run = CourseRunFactory(enrollment_end=None, end=None)

        # The course run should be open between its start of enrollment and its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.start.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": course_run.start,
            },
        )

        # The course run should be on-going & open forever after its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.start.timestamp()) + 1,
                int(datetime(9999, 12, 31).timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 0,
                "text": "forever open",
                "call_to_action": "enroll now",
                "datetime": None,
            },
        )

    def test_models_course_run_state_archived_open_closing_on(self):
        """
        A course run that is passed and has an enrollment end in the future should return
        a state with priority 2 and "closing on" as text.
        """
        course_run = CourseRunFactory(
            start=self.now - timedelta(hours=2),
            end=self.now - timedelta(hours=1),
            enrollment_end=self.now + timedelta(hours=1),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 2,
                "text": "closing on",
                "call_to_action": "study now",
                "datetime": course_run.enrollment_end,
            },
        )

    def test_models_course_run_state_archived_closed(self):
        """
        A course run that is passed should return a state with priority 6 and "archived"
        as text.
        """
        course_run = CourseRunFactory(
            start=self.now - timedelta(hours=2),
            end=self.now - timedelta(hours=1),
            enrollment_end=self.now - timedelta(hours=1),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 6,
                "text": "archived",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_ongoing_open(self):
        """
        A course run that is on-going and open for enrollment should return a state with a CTA
        to enroll and the date of the end of enrollment.
        """
        course_run = CourseRunFactory(
            enrollment_start=self.now - timedelta(hours=3),
            start=self.now - timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
            end=self.now + timedelta(hours=2),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 0,
                "text": "closing on",
                "call_to_action": "enroll now",
                "datetime": self.now + timedelta(hours=1),
            },
        )

    def test_models_course_run_state_ongoing_closed(self):
        """
        A course run that is on-going but closed for enrollment should return a state with
        "on-going" as text and no CTA.
        """
        course_run = CourseRunFactory(
            enrollment_start=self.now - timedelta(hours=3),
            start=self.now - timedelta(hours=2),
            enrollment_end=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=1),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 5,
                "text": "on-going",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_coming(self):
        """
        A course run that is future and not yet open for enrollment should return a state
        with a CTA to see details with the start date.
        """
        course_run = CourseRunFactory(
            enrollment_start=self.now + timedelta(hours=1),
            enrollment_end=self.now + timedelta(hours=2),
            start=self.now + timedelta(hours=3),
            end=self.now + timedelta(hours=4),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 3,
                "text": "starting on",
                "call_to_action": None,
                "datetime": self.now + timedelta(hours=3),
            },
        )

    def test_models_course_run_state_future_open(self):
        """
        A course run that is future and open for enrollment should return a state with a CTA
        to enroll and the start date.
        """
        course_run = CourseRunFactory(
            enrollment_start=self.now - timedelta(hours=1),
            enrollment_end=self.now + timedelta(hours=1),
            start=self.now + timedelta(hours=2),
            end=self.now + timedelta(hours=3),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": self.now + timedelta(hours=2),
            },
        )

    def test_models_course_run_state_future_closed(self):
        """
        A course run that is future and already closed for enrollment should return a state
        with "enrollment closed" as text and no CTA.
        """
        course_run = CourseRunFactory(
            enrollment_start=self.now - timedelta(hours=2),
            enrollment_end=self.now - timedelta(hours=1),
            start=self.now + timedelta(hours=1),
            end=self.now + timedelta(hours=2),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 4,
                "text": "enrollment closed",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_validation_on_update(self):
        """
        When the course field of a course run instance is updated,
        a ValidationError should be raised it the course run instance relies on
        product/order relation.
        """
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(target_courses=[course_run.course])

        # - Link course run to the product course relation
        relation = product.target_course_relations.first()
        relation.course_runs.add(course_run)

        # - Try to update the course of the course run
        course_run.course = factories.CourseFactory()
        with self.assertRaises(ValidationError) as context:
            course_run.save()

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['This course run relies on a product relation. "
                "So you cannot modify its course.']}"
            ),
        )

    def test_model_course_run_get_serialized(self):
        """
        Test the get_serialized method of the CourseRun model.
        catalog_visibility is set to hidden if the course run is not listed
        """
        course_run = factories.CourseRunFactory(
            is_listed=True,
            start=datetime(2022, 6, 6, 6, 0, tzinfo=ZoneInfo("UTC")),
            end=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2022, 9, 9, 9, 0, tzinfo=ZoneInfo("UTC")),
        )
        self.assertEqual(
            course_run.get_serialized(),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "course_and_search",
            },
        )
        course_run.is_listed = False
        course_run.save()
        self.assertEqual(
            course_run.get_serialized(),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "hidden",
            },
        )

    def test_model_course_run_get_serialized_hidden(self):
        """
        Test the get_serialized method of the CourseRun model when
        the parameter visibility is set to hidden.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 6, 6, 6, 0, tzinfo=ZoneInfo("UTC")),
            end=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2022, 9, 9, 9, 0, tzinfo=ZoneInfo("UTC")),
        )

        self.assertEqual(
            course_run.get_serialized(visibility="hidden"),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "hidden",
            },
        )

    def test_model_course_run_get_serialized_course_only(self):
        """
        Test the get_serialized method of the CourseRun model when
        the parameter visibility is set to course_only, catalog_visibility has the right value
        """
        course_run = factories.CourseRunFactory()

        self.assertEqual(
            course_run.get_serialized(visibility="course_only")["catalog_visibility"],
            "course_only",
        )

    def test_model_course_run_get_serialized_with_invalid_visibility(
        self,
    ):
        """
        Test the get_serialized method of the CourseRun model can only have
        expected values for visibility
        """
        course_run = factories.CourseRunFactory()
        with self.assertRaises(ValueError) as context:
            course_run.get_serialized(visibility="invalid_visibility")
            self.assertEqual(
                str(context.exception),
                (
                    "Invalid visibility value. Must be one of : "
                    "COURSE_AND_SEARCH, COURSE_ONLY, HIDDEN"
                ),
            )
