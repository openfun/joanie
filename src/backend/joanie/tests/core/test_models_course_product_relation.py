"""
Test suite for CourseProductRelation model
"""

from django.test import TestCase

from joanie.core import factories


class CourseProductRelationModelTestCase(TestCase):
    """Test suite for the CourseProductRelation model."""

    def test_model_course_product_relation_uri(self):
        """
        CourseProductRelation instance should have a property `uri`
        that returns the API url to get instance detail.
        """
        relation = factories.CourseProductRelationFactory(course__code="C_0001-2")

        self.assertEqual(
            relation.uri,
            (
                "https://example.com/api/v1.0/"
                f"courses/{relation.course.code}/products/{relation.product.id}/"
            ),
        )

    def test_model_course_product_relation_can_edit(self):
        """
        CourseProductRelation can_edit property should return True if the
        relation is not linked to any order, False otherwise.
        """
        relation = factories.CourseProductRelationFactory()
        self.assertTrue(relation.can_edit)

        factories.OrderFactory(
            product=relation.product,
            course=relation.course,
        )
        self.assertFalse(relation.can_edit)
