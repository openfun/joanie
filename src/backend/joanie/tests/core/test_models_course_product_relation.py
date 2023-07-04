"""
Test suite for CourseProductRelation model
"""
from django.test import TestCase

from joanie.core import factories


class CourseProductRelationModelTestCase(TestCase):
    """Test suite for the CourseProductRelation model."""

    def test_model_course_product_relation_get_read_detail_api_url(self):
        """
        CourseProductRelation instance should have a method `get_read_detail_api_url`
        that returns the API url to get instance detail.
        """
        relation = factories.CourseProductRelationFactory()

        self.assertEqual(
            relation.get_read_detail_api_url(),
            (
                "https://example.com/api/v1.0/"
                f"courses/{relation.course.code}/products/{relation.product.id}/"
            ),
        )
