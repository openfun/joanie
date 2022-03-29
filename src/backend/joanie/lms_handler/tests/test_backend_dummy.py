"""Test suite for the Dummy LMS Backend"""

from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings

from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.dummy import DummyLMSBackend


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
            "BASE_URL": "http://dummy-lms.test",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r".*",
        }
    ]
)
class DummyLMSBackendTestCase(TestCase):
    """Test suite for the Dummy LMS Backend."""

    def setUp(self):
        """Clears the cache before each test"""
        cache.clear()

    def test_backend_dummy_get_enrollment_not_set(self):
        """
        If user is not enrolled,
        get_enrollment should return a fake course run enrollment object
        marked "inactive".
        """
        resource_link = (
            "http://dummy-lms.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        username = "joanie"

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, DummyLMSBackend)

        # Should return None when user is not enrolled
        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(enrollment["user"], username)
        self.assertEqual(
            enrollment["course_details"]["course_id"],
            "course-v1:edx+000001+Demo_Course",
        )
        self.assertFalse(enrollment["is_active"])

    def test_backend_dummy_set_and_get_enrollment(self):
        """
        If user is enrolled,
        set_enrollment should return True
        get_enrollment should return a fake course run enrollment object
        marked "active".
        """
        resource_link = (
            "http://dummy-lms.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        username = "joanie"

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, DummyLMSBackend)

        backend.set_enrollment(username, resource_link, True)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(enrollment["user"], username)
        self.assertEqual(
            enrollment["course_details"]["course_id"],
            "course-v1:edx+000001+Demo_Course",
        )
        self.assertTrue(enrollment["is_active"])

    def test_backend_dummy_set_and_get_unenrollment(self):
        """
        On user unrollment
        set_enrollment should return True
        get_enrollment should return a fake course run enrollment object
        marked "inactive".
        """
        resource_link = (
            "http://dummy-lms.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        username = "joanie"

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, DummyLMSBackend)

        backend.set_enrollment(username, resource_link, False)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(enrollment["user"], username)
        self.assertEqual(
            enrollment["course_details"]["course_id"],
            "course-v1:edx+000001+Demo_Course",
        )
        self.assertFalse(enrollment["is_active"])

    def test_backend_dummy_get_grades(self):
        """It should return a blank grade dictionary"""
        username = "joanie"
        resource_link = (
            "http://dummy-lms.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, DummyLMSBackend)

        grade_summary = backend.get_grades(username, resource_link)

        # - grade summary should contain 6 properties
        self.assertEqual(len(grade_summary), 6)

        # - a boolean `passed`
        self.assertEqual(grade_summary["passed"], True)

        # - a string `grade`
        self.assertEqual(grade_summary["grade"], "A")

        # - a float `percent`
        self.assertEqual(grade_summary["percent"], 1.0)

        # - a dict `totaled_scores`
        self.assertEqual(
            grade_summary["totaled_scores"],
            {"Final Exam": [[1.0, 1.0, True, "First section", None]]},
        )

        # - a list `grade_breakdown`
        self.assertEqual(
            grade_summary["grade_breakdown"],
            [
                {
                    "category": "Final Exam",
                    "percent": 1.0,
                    "detail": "Final Exam = 100.00% of a possible 100.00%",
                }
            ],
        )

        # - a list `section_breakdown`
        self.assertEqual(
            grade_summary["section_breakdown"],
            [
                {
                    "category": "Final Exam",
                    "prominent": True,
                    "percent": 1.0,
                    "detail": "Final Exam = 100%",
                    "label": "FE",
                }
            ],
        )
