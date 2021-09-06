"""
Test suite for order models
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core import factories


class CourseRunModelsTestCase(TestCase):
    """Test suite for the CourseRun model."""

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

    def test_models_course_run_unique(self):
        """The resource link field should be unique."""
        course_run = factories.CourseRunFactory()

        with self.assertRaises(ValidationError) as context:
            factories.CourseRunFactory(resource_link=course_run.resource_link)

        self.assertEqual(
            "{'resource_link': ['Course run with this Resource link already exists.']}",
            str(context.exception),
        )
