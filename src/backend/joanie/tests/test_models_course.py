"""
Test suite for order models
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

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
