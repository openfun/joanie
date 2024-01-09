"""Test suite for the LMSHandler class."""
from django.test import TestCase
from django.test.utils import override_settings

from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.base import BaseLMSBackend
from joanie.lms_handler.backends.moodle import MoodleLMSBackend
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


class LMSHandlerTestCase(TestCase):
    """Test suite for the LMSHandler class."""

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
            },
            {
                "API_TOKEN": "LMS_API_TOKEN",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test",
                "SELECTOR_REGEX": r".*moodle.test.*",
            },
        ]
    )
    def test_lms_handler_select_lms(self):
        """
        The "select_lms" util function should return the right backend instance
        with its configuration or return None if the url does not match any backend.
        """
        backend = LMSHandler.select_lms("http://openedx.test/courses/42")
        self.assertIsInstance(backend, OpenEdXLMSBackend)
        self.assertEqual(backend.configuration["BASE_URL"], "http://openedx.test")

        backend = LMSHandler.select_lms("http://moodle.test/courses/42")
        self.assertIsInstance(backend, MoodleLMSBackend)
        self.assertEqual(backend.configuration["BASE_URL"], "http://moodle.test")

        backend = LMSHandler.select_lms("http://unknown-lms.test/courses/42")
        self.assertIsNone(backend)

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.base.BaseLMSBackend",
                "BASE_URL": "http://lms-1.test",
                "SELECTOR_REGEX": r"^disabled$",
            },
            {
                "API_TOKEN": "LMS_2_API_TOKEN",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://lms-2.test",
                "SELECTOR_REGEX": r"^disabled$",
                "COURSE_REGEX": r"^disabled$",
            },
            {
                "API_TOKEN": "LMS_3_API_TOKEN",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^disabled$",
                "SELECTOR_REGEX": r"^disabled$",
            },
        ]
    )
    def test_lms_handler_select_lms_no_match(self):
        """
        The "select_lms" util function should return None if the url does not match any backend.
        The "SELECTOR_REGEX" is disabled for all backends in this test.
        """
        backend = LMSHandler.select_lms("http://openedx.test/courses/42")
        self.assertIsNone(backend)

        backend = LMSHandler.select_lms("http://moodle.test/courses/42")
        self.assertIsNone(backend)

        backend = LMSHandler.select_lms("http://unknown-lms.test/courses/42")
        self.assertIsNone(backend)

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.base.BaseLMSBackend",
                "BASE_URL": "http://lms-1.test",
                "SELECTOR_REGEX": r".*",
            },
            {
                "API_TOKEN": "LMS_2_API_TOKEN",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "BASE_URL": "http://lms-2.test",
                "SELECTOR_REGEX": r".*",
                "COURSE_REGEX": r".*",
            },
            {
                "API_TOKEN": "LMS_3_API_TOKEN",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            },
        ]
    )
    def test_lms_handler_get_all_lms(self):
        """
        The "get_all_lms" util function should return all lms backend instances
        with its configuration.
        """
        backends = LMSHandler.get_all_lms()
        self.assertEqual(len(backends), 3)

        [first_lms, second_lms, third_lms] = backends
        # First LMS should be BaseLMSBackend
        self.assertIsInstance(first_lms, BaseLMSBackend)
        self.assertEqual(first_lms.configuration["BASE_URL"], "http://lms-1.test")
        self.assertEqual(first_lms.configuration["SELECTOR_REGEX"], r".*")

        # Second LMS should be OpenEdXLMSBackend
        self.assertIsInstance(second_lms, OpenEdXLMSBackend)
        self.assertEqual(second_lms.configuration["API_TOKEN"], "LMS_2_API_TOKEN")
        self.assertEqual(second_lms.configuration["BASE_URL"], "http://lms-2.test")
        self.assertEqual(second_lms.configuration["SELECTOR_REGEX"], r".*")
        self.assertEqual(second_lms.configuration["COURSE_REGEX"], r".*")

        # Third LMS should be MoodleLMSBackend
        self.assertIsInstance(third_lms, MoodleLMSBackend)
        self.assertEqual(third_lms.configuration["API_TOKEN"], "LMS_3_API_TOKEN")
        self.assertEqual(
            third_lms.configuration["BASE_URL"],
            "http://moodle.test/webservice/rest/server.php",
        )
        self.assertEqual(
            third_lms.configuration["SELECTOR_REGEX"], r"^.*/course/view.php\?id=.*$"
        )
        self.assertEqual(
            third_lms.configuration["COURSE_REGEX"], r"^.*/course/view.php\?id=.*$"
        )
