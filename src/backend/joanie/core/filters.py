"""
API Resource Filters
"""
from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from . import models
from .enums import (
    ORDER_STATE_CANCELED,
    ORDER_STATE_CHOICES,
    ORDER_STATE_PENDING,
    ORDER_STATE_VALIDATED,
)


class OrderViewSetFilter(filters.FilterSet):
    """
    OrderFilter allows to filter this resource with a product id or its state.
    """

    product = filters.UUIDFilter(field_name="product")
    course = filters.CharFilter(field_name="course__code")
    state = filters.ChoiceFilter(method="state_filter", choices=ORDER_STATE_CHOICES)

    class Meta:
        model = models.Order
        fields: List[str] = []

    def state_filter(self, queryset, _, value):
        """
        Filter orders by state. State property is a computed property, so we have to
        create manually query set filter according to the provided filter value
        """

        if value == ORDER_STATE_CANCELED:
            return queryset.filter(is_canceled=True)

        if value == ORDER_STATE_PENDING:
            return queryset.filter(
                total__gt=0,
                proforma_invoices__isnull=True,
                is_canceled=False,
            )

        if value == ORDER_STATE_VALIDATED:
            return queryset.filter(
                Q(total=0) | Q(proforma_invoices__isnull=False),
                is_canceled=False,
            )

        return queryset


class ProductViewSetFilter(filters.FilterSet):
    """
    ProductViewSetFilter allows to filter this resource with a course code.
    """

    course = filters.CharFilter(field_name="courses__code")

    class Meta:
        model = models.Product
        fields: List[str] = []
