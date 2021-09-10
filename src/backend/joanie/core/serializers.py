"""Serializers for api."""
from rest_framework import serializers

from joanie.core import models


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer including list of course runs with its positions
    """

    id = serializers.CharField(source="uid", read_only=True)

    class Meta:
        model = models.Product
        fields = ["id", "title", "call_to_action", "price"]


class CourseSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course.
    """

    organization = serializers.CharField(source="organization.code", read_only=True)
    products = serializers.SlugRelatedField(many=True, read_only=True, slug_field="uid")

    class Meta:
        model = models.Course
        fields = [
            "code",
            "organization",
            "title",
            "products",
        ]


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
        return obj.course_run.course.product_relations.get(
            product=obj.order.product
        ).position


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)
    user = serializers.CharField(source="user.username", read_only=True, required=False)
    course_run = serializers.SlugRelatedField(
        queryset=models.CourseRun.objects.all(), slug_field="resource_link"
    )
    order = serializers.SlugRelatedField(
        queryset=models.Order.objects.all(), slug_field="uid", required=False
    )

    class Meta:
        model = models.Enrollment
        fields = ["id", "user", "course_run", "order", "is_active", "state"]
        read_only_fields = ["state"]

    def update(self, instance, validated_data):
        """
        Restrict the values that can be set from the API for the state field to "set".
        The "failed" state can only be set by the LMSHandler.
        """
        validated_data.pop("course_run", None)
        validated_data.pop("order", None)
        return super().update(instance, validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = serializers.SlugRelatedField(
        queryset=models.Course.objects.all(), slug_field="code"
    )
    product = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="uid"
    )
    enrollments = CourseRunEnrollmentSerializer(
        many=True, read_only=True, required=False
    )
    target_courses = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Order
        fields = [
            "id",
            "course",
            "created_on",
            "enrollments",
            "owner",
            "price",
            "product",
            "state",
            "target_courses",
        ]
        read_only_fields = [
            "created_on",
            "state",
            "price",
        ]

    @staticmethod
    def get_target_courses(obj):
        """Compute the serialized value for the "target_courses" field."""
        return (
            models.Course.objects.filter(order_relations__order=obj)
            .order_by("order_relations__position")
            .values_list("code", flat=True)
        )

    def update(self, instance, validated_data):
        """Make the "course" and "product" fields read_only only on update."""
        validated_data.pop("course", None)
        validated_data.pop("product", None)
        return super().update(instance, validated_data)


class AddressSerializer(serializers.ModelSerializer):
    """
    Address model serializer
    """

    id = serializers.CharField(source="uid", required=False)

    class Meta:
        model = models.Address
        fields = [
            "address",
            "city",
            "country",
            "fullname",
            "id",
            "is_main",
            "postcode",
            "title",
        ]
