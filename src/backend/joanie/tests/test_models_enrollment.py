"""
Test suite for order models
"""
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import factories
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


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
class EnrollmentModelsTestCase(TestCase):
    """Test suite for the Enrollment model."""

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_str_active(self, _mock_set):
        """The string representation should work as expected for an active enrollment."""
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            title="my run",
            resource_link=resource_link,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=True,
        )

        self.assertEqual(
            str(enrollment),
            (
                "[active][set] Françoise for my run "
                f"[{course_run.start:%Y-%m-%d} to {course_run.end:%Y-%m-%d}]"
            ),
        )

    def test_models_enrollment_str_inactive(self):
        """The string representation should work as expected for an inactive enrollment."""

        course_run = factories.CourseRunFactory(
            title="my run",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=False,
        )

        self.assertEqual(
            str(enrollment),
            (
                "[inactive][failed] Françoise for my run "
                f"[{course_run.start:%Y-%m-%d} to {course_run.end:%Y-%m-%d}]"
            ),
        )

    def test_models_enrollment_unique_course_run_user(self):
        """
        A user can only have one enrollment on a given course run.
        """
        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run)
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=enrollment.course_run, user=enrollment.user
            )
        self.assertEqual(
            "{'__all__': ['Enrollment with this Course run and User already exists.']}",
            str(context.exception),
        )
