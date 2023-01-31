"""Test suite for the TargetCourseSerializer"""
from collections import OrderedDict

from django.test import TestCase

from rest_framework import serializers

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
        organizations = factories.OrganizationFactory.create_batch(2)
        course = factories.CourseFactory(organizations=organizations)
        course_runs = CourseRunSerializer().to_representation(course.course_runs)
        organizations = OrganizationSerializer().to_representation(organizations)

        data = {
            "code": str(course.code),
            "course_runs": course_runs,
            "is_graded": False,
            "organizations": organizations,
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

        with self.assertNumQueries(6):
            representation = TargetCourseSerializer(
                context={"resource": product}
            ).to_representation(target_course)

        # - Product should target the two course runs
        self.assertEqual(product.target_course_runs.count(), 2)

        # - So all course runs are returned
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 2)

    def test_serializer_target_course_get_course_runs_if_order_relation_course_runs_is_empty(
        self,
    ):
        """
        If the target course order relation has no course runs, course runs from the
        course itself should be returned.
        """
        target_course = factories.CourseFactory()
        factories.CourseRunFactory.create_batch(2, course=target_course)
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(product=product)

        with self.assertNumQueries(6):
            representation = TargetCourseSerializer(
                context={"resource": order}
            ).to_representation(target_course)

        # - Order should target the two course runs
        self.assertEqual(order.target_course_runs.count(), 2)

        # - So all course runs are returned
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 2)

    def test_serializer_target_course_without_resource_in_context(
        self,
    ):
        """
        If no resource is provided through serializer context, an exception should be
        raised when getting serializer representation.
        """
        target_course = factories.CourseFactory()

        with self.assertRaises(serializers.ValidationError) as context:
            TargetCourseSerializer().to_representation(target_course)

        self.assertEqual(
            str(context.exception),
            (
                "[ErrorDetail(string='TargetCourseSerializer context must contain a "
                "\"resource\" property.', code='invalid')]"
            ),
        )

    def test_serializer_target_course_with_invalid_resource_in_context(
        self,
    ):
        """
        If something else than Product or Order is provided as resource through
        serializer context, an exception should be raised when getting serializer
        representation.
        """
        target_course = factories.CourseFactory()

        with self.assertRaises(serializers.ValidationError) as context:
            TargetCourseSerializer(
                context={"resource": factories.CourseFactory()}
            ).to_representation(target_course)

        self.assertEqual(
            str(context.exception),
            (
                "[ErrorDetail(string='TargetCourseSerializer context resource property "
                "must be instance of Product or Order.', code='invalid')]"
            ),
        )

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
        relation = target_course.product_target_relations.get(product=product)
        relation.course_runs.set([course_run])

        representation = TargetCourseSerializer(
            context={"resource": product}
        ).to_representation(instance=target_course)

        # - Product should target only one course run
        self.assertEqual(product.target_course_runs.count(), 1)

        # - So target_course.product_relations.course_runs are used
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 1)
        self.assertEqual(course_runs_repr[0]["id"], str(course_run.pk))

    def test_serializer_target_course_get_order_relation_course_runs_if_there_are(
        self,
    ):
        """
        If the target course order relation has course runs, they should be used to populate
        the course runs field
        """
        target_course = factories.CourseFactory()
        course_run, _ = factories.CourseRunFactory.create_batch(2, course=target_course)
        product = factories.ProductFactory(target_courses=[target_course])

        # - Link only one course run to the product course relation
        relation = target_course.product_target_relations.get(product=product)
        relation.course_runs.set([course_run])

        # - Create an order related to the product
        order = factories.OrderFactory(product=product)

        representation = TargetCourseSerializer(
            context={"resource": order}
        ).to_representation(instance=target_course)

        # - Product should target only one course run
        self.assertEqual(order.target_course_runs.count(), 1)

        # - So target_course.product_relations.course_runs are used
        course_runs_repr = representation["course_runs"]
        self.assertEqual(len(course_runs_repr), 1)
        self.assertEqual(course_runs_repr[0]["id"], str(course_run.pk))
