"""
Test suite for order models
"""
from django.test import TestCase

from joanie.core import factories


class CourseRunModelsTestCase(TestCase):
    """Test suite for the CourseRun model."""

    def test_models_course_run(self):
        """
        The resource_link field should be normalized on save.
        """
        course_run = factories.CourseRunFactory()
        course_run.resource_link = "https://www.Example.Com:443/Capitalized-Path"
        course_run.save()
        self.assertEqual(
            course_run.resource_link, "https://www.example.com/Capitalized-Path"
        )
