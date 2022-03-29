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
from joanie.core.exceptions import GradeError
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

    @override_settings(JOANIE_ENROLLMENT_GRADE_CACHE_TTL=600)
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    @mock.patch.object(OpenEdXLMSBackend, "get_grades", return_value={"passed": True})
    def test_models_enrollment_is_passed(self, mock_get_grades, _):
        """
        The `is_passed` property should use the get_grades method of the LMS to retrieve
        information then store in cache the result.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            resource_link=resource_link,
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run)

        self.assertIs(enrollment.is_passed, True)
        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )

        # - Call it again should return the same result
        mock_get_grades.reset_mock()
        self.assertIs(enrollment.is_passed, True)
        # - But `get_grades` should not have been called again
        mock_get_grades.assert_not_called()

    @override_settings(JOANIE_ENROLLMENT_GRADE_CACHE_TTL=600)
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    @mock.patch.object(OpenEdXLMSBackend, "get_grades", side_effect=GradeError())
    def test_models_enrollment_is_passed_not_cached_on_failure(
        self, mock_get_grades, _
    ):
        """
        In case of get_grades LMS request fails, `is_passed` property should be False
        and the result should not be cached.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            resource_link=resource_link,
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run)

        self.assertIs(enrollment.is_passed, False)

        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )

        # - Calling it again should trigger the `get_grades` method
        mock_get_grades.reset_mock()
        mock_get_grades.return_value = {"passed": True}
        mock_get_grades.side_effect = None
        self.assertIs(enrollment.is_passed, True)
        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )
