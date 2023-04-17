"""
Client API Resource Filters
"""
from typing import List

from django_filters import rest_framework as filters

from .. import models
from ..enums import ORDER_STATE_CHOICES


class OrderViewSetFilter(filters.FilterSet):
    """
    OrderFilter allows to filter this resource with a product id or its state.
    """

    product = filters.UUIDFilter(field_name="product")
    course = filters.CharFilter(field_name="course__code")
    state = filters.ChoiceFilter(field_name="state", choices=ORDER_STATE_CHOICES)

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
