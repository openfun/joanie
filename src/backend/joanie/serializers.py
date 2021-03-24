"""Serializers for api."""
from rest_framework import serializers

from joanie.core import models


class ProductCourseRunPositionSerializer(serializers.ModelSerializer):
    """
    Serialize all information about each course run inside a product
    all course run information and course run position for the product
    """

    resource_link = serializers.CharField(source="course_run.resource_link")
    title = serializers.CharField(source="course_run.title")
    start = serializers.CharField(source="course_run.start")
    end = serializers.CharField(source="course_run.end")
    enrollment_start = serializers.CharField(source="course_run.enrollment_start")
    enrollment_end = serializers.CharField(source="course_run.enrollment_end")

    class Meta:
        model = models.ProductCourseRunPosition
        fields = [
            "position",
            "resource_link",
            "title",
            "start",
            "end",
            "enrollment_start",
            "enrollment_end",
        ]


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer including list of course runs with its positions
    """

    id = serializers.CharField(source="uid")
    course_runs = serializers.SerializerMethodField()

    class Meta:
        model = models.Product
        fields = ["id", "title", "call_to_action", "course_runs", "price"]

    @staticmethod
    def get_course_runs(obj):
        """
        Get list of course runs available and its positions for a product.
        Sort by course run position then start date.
        """
        return ProductCourseRunPositionSerializer(
            obj.course_runs_positions.select_related("course_run").order_by(
                "position", "course_run__start"
            ),
            many=True,
        ).data


class CourseRunEnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment for course run serializer
    """

    resource_link = serializers.CharField(source="course_run.resource_link")
    title = serializers.CharField(source="course_run.title")
    start = serializers.CharField(source="course_run.start")
    end = serializers.CharField(source="course_run.end")
    enrollment_start = serializers.CharField(source="course_run.enrollment_start")
    enrollment_end = serializers.CharField(source="course_run.enrollment_end")
    position = serializers.SerializerMethodField()

    class Meta:
        model = models.Enrollment
        fields = [
            "resource_link",
            "title",
            "start",
            "end",
            "enrollment_start",
            "enrollment_end",
            "state",
            "position",
        ]

    @staticmethod
    def get_position(obj):
        """Get position of course run linked for a product"""
        return obj.course_run.positions.get(product=obj.order.product).position


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(source="uid")
    enrollments = CourseRunEnrollmentSerializer(many=True)
    owner = serializers.CharField(source="owner.username")
    product_id = serializers.CharField(source="product.uid")

    class Meta:
        model = models.Order
        fields = ["id", "created_on", "state", "owner", "product_id", "enrollments"]
