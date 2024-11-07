"""Test case for the course run utility `aggregate_course_runs_dates` method."""

from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from joanie.core import factories
from joanie.core.factories import CourseFactory
from joanie.core.utils.course_run import aggregate_course_runs_dates


class UtilsCourseRunAggregateDatesTestCase(TestCase):
    """Test suite for the course run utility `aggregate_course_runs_dates` method."""

    maxDiff = None

    def test_utils_course_run_aggregate_dates(self):
        """
        It should aggregate the dates of all course runs provided. By default, archived
        course runs are included.
        """
        mocked_now = datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC"))
        archived_run = factories.CourseRunFactory(
            start=datetime(2024, 11, 1, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 11, 30, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2024, 10, 1, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2024, 10, 31, tzinfo=ZoneInfo("UTC")),
        )
        ongoing_run = factories.CourseRunFactory(
            start=datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2024, 11, 1, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2024, 11, 30, tzinfo=ZoneInfo("UTC")),
        )

        course = factories.CourseFactory(course_runs=[archived_run, ongoing_run])

        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            dates = aggregate_course_runs_dates(course.course_runs)

        self.assertDictEqual(
            dates,
            {
                "start": archived_run.start,
                "end": ongoing_run.end,
                "enrollment_start": ongoing_run.enrollment_start,
                "enrollment_end": archived_run.enrollment_end,
            },
        )

    def test_utils_course_run_aggregate_dates_ignore_archived(self):
        """
        It should aggregate the dates of all course runs provided and ignore the archived ones.
        """
        mocked_now = datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC"))
        archived_run = factories.CourseRunFactory(
            start=datetime(2024, 11, 1, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 11, 30, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2024, 10, 1, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2024, 10, 31, tzinfo=ZoneInfo("UTC")),
        )
        ongoing_run = factories.CourseRunFactory(
            start=datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2024, 11, 1, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2024, 11, 30, tzinfo=ZoneInfo("UTC")),
        )
        course = factories.CourseFactory(course_runs=[archived_run, ongoing_run])

        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            dates = aggregate_course_runs_dates(
                course.course_runs, ignore_archived=True
            )

        self.assertDictEqual(
            dates,
            {
                "start": ongoing_run.start,
                "end": ongoing_run.end,
                "enrollment_start": ongoing_run.enrollment_start,
                "enrollment_end": ongoing_run.enrollment_end,
            },
        )

    def test_utils_course_run_aggregate_dates_empty_queryset(self):
        """
        It should return a dict with `None` values if the course run queryset is empty.
        """
        course = CourseFactory()

        dates = aggregate_course_runs_dates(course.course_runs)

        self.assertEqual(course.course_runs.count(), 0)
        self.assertEqual(
            dates,
            {
                "start": None,
                "end": None,
                "enrollment_start": None,
                "enrollment_end": None,
            },
        )
