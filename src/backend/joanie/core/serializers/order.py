"""Order serializers"""
from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

from joanie.core import models

from .course import CourseSerializer, TargetCourseSerializer
from .enrollment import EnrollmentSerializer
from .organization import OrganizationSerializer


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = serializers.SlugRelatedField(
        queryset=models.Course.objects.all(), slug_field="code"
    )
    total = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
        required=False,
    )
    organization = serializers.SlugRelatedField(
        queryset=models.Organization.objects.all(), slug_field="id", required=False
    )
    product = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="id"
    )
    enrollments = serializers.SerializerMethodField(read_only=True)
    target_courses = serializers.SerializerMethodField(read_only=True)
    main_invoice = serializers.SlugRelatedField(read_only=True, slug_field="reference")
    certificate = serializers.SlugRelatedField(read_only=True, slug_field="id")

    class Meta:
        model = models.Order
        fields = [
            "course",
            "created_on",
            "certificate",
            "enrollments",
            "id",
            "main_invoice",
            "organization",
            "owner",
            "total",
            "total_currency",
            "product",
            "state",
            "target_courses",
        ]
        read_only_fields = [
            "certificate",
            "created_on",
            "enrollments",
            "id",
            "main_invoice",
            "owner",
            "total",
            "total_currency",
            "state",
            "target_courses",
        ]

    def get_target_courses(self, order):
        """Compute the serialized value for the "target_courses" field."""
        context = self.context.copy()
        context["resource"] = order

        return TargetCourseSerializer(
            instance=order.target_courses.all().order_by("order_relations__position"),
            many=True,
            context=context,
        ).data

    def get_enrollments(self, order):
        """
        For the current order, retrieve its related enrollments.
        """
        return EnrollmentSerializer(
            instance=order.get_enrollments(),
            many=True,
            context=self.context,
        ).data

    def update(self, instance, validated_data):
        """Make the "course" and "product" fields read_only only on update."""
        validated_data.pop("course", None)
        validated_data.pop("organization", None)
        validated_data.pop("product", None)
        return super().update(instance, validated_data)


class CertificateOrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer for the Certificate model
    """

    id = serializers.CharField(read_only=True, required=False)
    course = CourseSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = models.Order
        fields = ["id", "course", "organization"]
        read_only_fields = ["id", "course", "organization"]
