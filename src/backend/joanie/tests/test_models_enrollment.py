"""
Test suite for order models
"""
from datetime import datetime
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

import pytz

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
        enrollment = factories.EnrollmentFactory(
            user__username="Françoise",
            course_run__title="my run",
            course_run__resource_link=resource_link,
            course_run__start=datetime(2021, 6, 12).replace(tzinfo=pytz.utc),
            course_run__end=datetime(2021, 6, 15).replace(tzinfo=pytz.utc),
            is_active=True,
        )
        self.assertEqual(
            str(enrollment),
            "[active][set] Françoise for my run [2021-06-12 to 2021-06-15]",
        )

    def test_models_enrollment_str_inactive(self):
        """The string representation should work as expected for an inactive enrollment."""
        enrollment = factories.EnrollmentFactory(
            user__username="Françoise",
            course_run__title="my run",
            course_run__start=datetime(2021, 6, 12).replace(tzinfo=pytz.utc),
            course_run__end=datetime(2021, 6, 15).replace(tzinfo=pytz.utc),
            is_active=False,
        )
        self.assertEqual(
            str(enrollment),
            "[inactive][failed] Françoise for my run [2021-06-12 to 2021-06-15]",
        )

    def test_models_enrollment_unique_course_run_user(self):
        """
        A user can only have one enrollment on a given course run.
        """
        enrollment = factories.EnrollmentFactory()
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=enrollment.course_run, user=enrollment.user
            )
        self.assertEqual(
            "{'__all__': ['Enrollment with this Course run and User already exists.']}",
            str(context.exception),
        )
