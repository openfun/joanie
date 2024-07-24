"""Test case for utils"""

from django.test import TestCase

from joanie.edx_imports.utils import extract_course_id


class UtilsTestCase(TestCase):
    """Test case for utils"""

    def test_utils_extract_course_id_no_match(self):
        """If nothing match, None should be returned"""
        self.assertIsNone(extract_course_id("https://openedx.com"))

    def test_utils_extract_course_id_matches(self):
        """It should support all kind of OpenEdX resource link."""
        resource_links = [
            ("https://openedx.com/courses/%s/course", "course-v1:fun+101+run01"),
            ("https://openedx.com/courses/%s/info", "course-v1:fun+101+run01"),
            ("https://openedx.com/courses/%s/course/", "course-v1:fun+101+run01"),
            ("https://openedx.com/courses/%s/info/", "course-v1:fun+101+run01"),
            ("https://openedx.com/courses/%s/course/", "fun/101/run01"),
            ("https://openedx.com/courses/%s/info/", "fun/101/run01"),
        ]

        for url, course_id in resource_links:
            resource_link = url % course_id
            self.assertEqual(extract_course_id(resource_link), course_id)
