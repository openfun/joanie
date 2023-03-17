"""Product serializers"""
from django.conf import settings
from django.core.cache import cache

from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

from joanie.core import models, utils
from joanie.core.enums import ORDER_STATE_PENDING, ORDER_STATE_VALIDATED

from .certificate_definition import CertificationDefinitionSerializer
from .course import TargetCourseSerializer
from .organization import OrganizationSerializer


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer including
        - certificate information if there is
        - targeted courses with its course runs
            - If user is authenticated, we try to retrieve enrollment related
              to each course run.
        - order if user is authenticated
    """

    id = serializers.CharField(read_only=True)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    organizations = serializers.SerializerMethodField("get_organizations")
    price = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
    )
    target_courses = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Product
        fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "organizations",
            "price",
            "price_currency",
            "target_courses",
            "title",
            "type",
        ]
        read_only_fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "organizations",
            "price",
            "price_currency",
            "target_courses",
            "title",
            "type",
        ]

    def get_target_courses(self, product):
        """
        For the current product, retrieve its related courses.
        """

        context = self.context.copy()
        context["resource"] = product

        return TargetCourseSerializer(
            instance=product.target_courses.all().order_by(
                "product_target_relations__position"
            ),
            many=True,
            context=context,
        ).data

    def get_organizations(self, instance):
        """Get related organizations when in the context of a course."""
        try:
            organizations = instance.annotated_course_relations[0].organizations.all()
        except AttributeError:
            if self.context.get("course_code"):
                organizations = models.CourseProductRelation.objects.get(
                    course__code=self.context["course_code"], product=instance
                ).organizations.all()
            else:
                organizations = []

        return OrganizationSerializer(organizations, many=True, read_only=True).data

    def get_orders(self, instance):
        """
        If a user is authenticated, it retrieves valid or pending orders related to the
        product instance. If a course code has been provided through query
        parameters orders are also filtered by course.
        """
        try:
            filters = {"owner__username": self.context["username"]}
        except KeyError:
            return None

        if course_code := self.context.get("course_code"):
            filters["course__code"] = course_code

        try:
            orders = models.Order.objects.filter(
                state__in=(ORDER_STATE_VALIDATED, ORDER_STATE_PENDING),
                product=instance,
                **filters,
            ).only("pk")
        except models.Order.DoesNotExist:
            return None

        return [order.pk for order in orders]

    def to_representation(self, instance):
        """
        Cache the serializer representation that does not vary from user to user
        then, if user is authenticated, add private information to the representation
        """
        cache_key = utils.get_resource_cache_key(
            "product_for_course",
            f"{instance.id!s}-{self.context.get('course_code', 'nocourse'):s}",
            is_language_sensitive=True,
        )
        representation = cache.get(cache_key)

        if representation is None:
            representation = super().to_representation(instance)
            cache.set(
                cache_key,
                representation,
                settings.JOANIE_ANONYMOUS_SERIALIZER_DEFAULT_CACHE_TTL,
            )

        representation["orders"] = self.get_orders(instance)

        return representation
