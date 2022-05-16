"""Test suite for the TargetCourseSerializer"""
from collections import OrderedDict

from django.test import TestCase

from joanie.core import factories
from joanie.core.serializers import (
    CourseRunSerializer,
    OrganizationSerializer,
    TargetCourseSerializer,
)


class TargetCourseSerializerTestCase(TestCase):
    """TargetCourseSerializer test case"""

    def test_serializer_target_course_is_read_only(self):
        """A target course should be read only."""
        course = factories.CourseFactory.build()
        course_runs = CourseRunSerializer().to_representation(course.course_runs)
        organization = OrganizationSerializer().to_representation(course.organization)

        data = {
            "code": str(course.code),
            "course_runs": course_runs,
            "is_graded": False,
            "organization": organization,
            "position": 9999,
            "title": course.title,
        }
        serializer = TargetCourseSerializer(data=data)

        # - Serializer should be valid
        self.assertTrue(serializer.is_valid())
        # - but validated data should be an empty ordered dict
        self.assertEqual(serializer.validated_data, OrderedDict([]))

    def test_serializer_target_course_get_course_runs_if_product_relation_course_runs_is_empty(
        self,
    ):
        """
        If the target course product relation has no course runs, course runs from the
        course itself should be returned.
        """
        target_course = factories.CourseFactory()
        factories.CourseRunFactory.create_batch(2, course=target_course)
        product = factories.ProductFactory(target_courses=[target_course])

        with self.assertNumQueries(5):
            representation = TargetCourseSerializer(
                context={"product": product}
            ).to_representation(target_course)

        # - No course runs are linked to product course relation
        self.assertEqual(
            target_course.product_relations.get(product=product).course_runs.count(), 0
        )

        # - So target_course.course_runs are used
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 2)

    def test_serializer_target_course_get_product_relation_course_runs_if_there_are(
        self,
    ):
        """
        If the target course product relation has course runs, they should be used to populate
        the course runs field
        """
        target_course = factories.CourseFactory()
        [course_run, _] = factories.CourseRunFactory.create_batch(
            2, course=target_course
        )
        product = factories.ProductFactory(target_courses=[target_course])

        # - Link only one course run to the product course relation
        relation = target_course.product_relations.get(product=product)
        relation.course_runs.set([course_run])

        representation = TargetCourseSerializer(
            context={"product": product}
        ).to_representation(instance=target_course)

        # - One course runs is linked to product course relation
        self.assertEqual(
            target_course.product_relations.get(product=product).course_runs.count(), 1
        )

        # - So target_course.product_relations.course_runs are used
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 1)
        self.assertEqual(course_runs_repr[0]["id"], course_run.pk)
