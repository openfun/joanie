"""
Client API Resource Filters
"""
from typing import List

from django_filters import rest_framework as filters

from joanie.core import enums, models


class OrderViewSetFilter(filters.FilterSet):
    """
    OrderFilter allows to filter this resource with a product id or its state.
    """

    product = filters.UUIDFilter(field_name="product")
    enrollment = filters.UUIDFilter(field_name="enrollment")
    course = filters.CharFilter(field_name="course__code")
    state = filters.MultipleChoiceFilter(
        field_name="state", choices=enums.ORDER_STATE_CHOICES
    )
    state__exclude = filters.MultipleChoiceFilter(
        field_name="state", choices=enums.ORDER_STATE_CHOICES, exclude=True
    )
    product__type = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
    )
    product__type__exclude = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
        exclude=True,
    )

    class Meta:
        model = models.Order
        fields: List[str] = []


class ProductViewSetFilter(filters.FilterSet):
    """
    ProductViewSetFilter allows to filter this resource with a course code.
    """

    course = filters.CharFilter(field_name="courses__code")

    class Meta:
        model = models.Product
        fields: List[str] = []


class EnrollmentViewSetFilter(filters.FilterSet):
    """
    EnrollmentViewSetFilter allows to filter this resource with a course run id.
    """

    course_run = filters.UUIDFilter(field_name="course_run__id")
    was_created_by_order = filters.BooleanFilter(field_name="was_created_by_order")

    class Meta:
        model = models.Enrollment
        fields: List[str] = []


class CourseViewSetFilter(filters.FilterSet):
    """
    CourseViewSetFilter allows to filter this resource according to if it has related
    course runs or not.
    """

    has_listed_course_runs = filters.BooleanFilter(
        method="filter_has_listed_course_runs"
    )

    product_type = filters.ChoiceFilter(
        choices=enums.PRODUCT_TYPE_CHOICES, method="filter_product_type"
    )

    class Meta:
        model = models.Course
        fields: List[str] = ["has_listed_course_runs", "product_type"]

    def filter_has_listed_course_runs(self, queryset, _name, value):
        """
        Filter courses by looking for related course runs which are listed.
        """
        if value is True:
            filtered_queryset = queryset.filter(course_runs__is_listed=True)
        else:
            filtered_queryset = queryset.exclude(course_runs__is_listed=True)

        return filtered_queryset.distinct()

    def filter_product_type(self, queryset, _name, value):
        """
        Filter courses by looking for related products with matching type
        """
        return queryset.filter(products__type=value).distinct()


class ContractViewSetFilter(filters.FilterSet):
    """ContractFilter allows to filter this resource with a signature state."""

    is_signed = filters.BooleanFilter(method="get_is_signed")

    class Meta:
        model = models.Contract
        fields: List[str] = ["is_signed"]

    def get_is_signed(self, queryset, _name, value):
        """
        Filter Contracts by signature status
        """
        return queryset.filter(signed_on__isnull=not value)
