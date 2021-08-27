"""
Test suite for order models
"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import translation

from joanie.core import factories, models


class CourseRunModelsTestCase(TestCase):
    """Test suite for the CourseRun model."""

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

    def test_models_course_get_cache_key(self):
        """
        The `get_cache_key` method should return a key related to the
        code and the active language
        """
        course = factories.CourseFactory(code="00001")
        self.assertEqual(course.get_cache_key(), "course-00001-en-us")

        # - Switch to french
        with translation.override("fr-fr"):
            self.assertEqual(course.get_cache_key(), "course-00001-fr-fr")

        # - Force language
        self.assertEqual(course.get_cache_key("de-de"), "course-00001-de-de")
