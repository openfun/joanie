"""
Client API Resource Filters
"""

from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from joanie.core import enums, models

from .certificate import CertificateViewSetFilter
from .enrollment import EnrollmentViewSetFilter


class OrderViewSetFilter(filters.FilterSet):
    """
    OrderFilter allows to filter this resource with a product id or its state.
    """

    product_id = filters.UUIDFilter(field_name="product")
    enrollment_id = filters.UUIDFilter(field_name="enrollment")
    course_code = filters.CharFilter(field_name="course__code")
    state = filters.MultipleChoiceFilter(
        field_name="state", choices=enums.ORDER_STATE_CHOICES
    )
    state_exclude = filters.MultipleChoiceFilter(
        field_name="state", choices=enums.ORDER_STATE_CHOICES, exclude=True
    )
    product_type = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
    )
    product_type_exclude = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
        exclude=True,
    )
    query = filters.CharFilter(method="filter_by_query")

    class Meta:
        model = models.Order
        fields: List[str] = []

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by product title
        """
        return queryset.filter(product__translations__title__icontains=value).distinct()


class ProductViewSetFilter(filters.FilterSet):
    """
    ProductViewSetFilter allows to filter this resource with a course code.
    """

    course_code = filters.CharFilter(field_name="courses__code")

    class Meta:
        model = models.Product
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
    query = filters.CharFilter(method="filter_by_query")

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

    def filter_by_query(self, queryset, _name, value):
        """
        Filter courses by looking for course title or course code
        """
        course_title_query = Q(translations__title__icontains=value)
        course_code_query = Q(code__icontains=value)
        combined_query = course_title_query | course_code_query

        if organization_id := self.request.resolver_match.kwargs.get("organization_id"):
            organization_filter = Q(organizations__in=[organization_id])
            combined_query &= organization_filter

        return queryset.filter(combined_query).distinct()


class ContractViewSetFilter(filters.FilterSet):
    """ContractFilter allows to filter this resource with a signature state."""

    signature_state = filters.ChoiceFilter(
        method="filter_signature_state",
        choices=enums.CONTRACT_SIGNATURE_STATE_FILTER_CHOICES,
    )
    id = filters.AllValuesMultipleFilter()
    course_id = filters.UUIDFilter(field_name="order__course__id")
    product_id = filters.UUIDFilter(field_name="order__product__id")
    organization_id = filters.UUIDFilter(field_name="order__organization__id")
    offer_id = filters.UUIDFilter(method="filter_offer_id")

    class Meta:
        model = models.Contract
        fields: List[str] = ["id", "signature_state", "offer_id"]

    def filter_signature_state(self, queryset, _name, value):
        """
        Filter Contracts by signature state
        """

        is_unsigned = value == enums.CONTRACT_SIGNATURE_STATE_UNSIGNED
        is_half_signed = value == enums.CONTRACT_SIGNATURE_STATE_HALF_SIGNED

        return queryset.filter(
            student_signed_on__isnull=is_unsigned,
            organization_signed_on__isnull=is_unsigned | is_half_signed,
        )

    def filter_offer_id(self, queryset, _name, value):
        """
        Try to retrieve an offer from the given id and filter
        contracts accordingly.
        """

        url_kwargs = self.request.parser_context.get("kwargs", {})

        # This filter can be used into nested routes (courses or organizations) so we need to
        # check if the offer is related to the current resource.
        queryset_filters = {"id": value}
        if course_id := url_kwargs.get("course_id"):
            queryset_filters["course_id"] = course_id
        if organization_id := url_kwargs.get("organization_id"):
            queryset_filters["organizations__in"] = [organization_id]

        try:
            offer = models.CourseProductRelation.objects.get(**queryset_filters)
        except models.CourseProductRelation.DoesNotExist:
            return queryset.none()

        return queryset.filter(
            order__course_id=offer.course_id,
            order__product_id=offer.product_id,
            order__organization__in=offer.organizations.only("pk").values_list(
                "pk", flat=True
            ),
        )


class NestedOrderCourseViewSetFilter(filters.FilterSet):
    """
    OrderCourseFilter that allows to filter this resource with a product's 'id', an
    organization's 'id' or an offer's 'id'.
    """

    offer_id = filters.UUIDFilter(
        method="filter_offer_id",
    )
    organization_id = filters.UUIDFilter(field_name="organization__id")
    product_id = filters.UUIDFilter(field_name="product__id")

    class Meta:
        model = models.Order
        fields: List[str] = ["offer_id"]

    def filter_offer_id(self, queryset, _name, value):
        """
        Get the offer linked to an order by its 'id'.
        """
        try:
            offer = models.CourseProductRelation.objects.get(
                id=value, course_id=self.request.resolver_match.kwargs.get("course_id")
            )
        except models.CourseProductRelation.DoesNotExist:
            return queryset.none()

        return queryset.filter(
            product_id=offer.product_id,
            organization__in=offer.organizations.only("pk").values_list(
                "pk", flat=True
            ),
        )


class OfferViewSetFilter(filters.FilterSet):
    """
    Filter offers by product type.
    """

    product_type = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
    )
    product_type_exclude = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
        exclude=True,
    )
    query = filters.CharFilter(method="filter_by_query")

    class Meta:
        model = models.CourseProductRelation
        fields: List[str] = []

    def filter_by_query(self, queryset, _name, value):
        """
        Filter offer by looking for product title | course code | organization
        title.
        """
        product_title_query = Q(product__translations__title__icontains=value)
        organization_title_query = Q(
            organizations__translations__title__icontains=value
        )
        course_code_query = Q(course__code__icontains=value)
        combined_query = (
            product_title_query | course_code_query | organization_title_query
        )

        if organization_id := self.request.resolver_match.kwargs.get("organization_id"):
            organization_filter = Q(organizations__in=[organization_id])
            combined_query &= organization_filter

        return queryset.filter(combined_query).distinct()


class OrganizationViewSetFilter(filters.FilterSet):
    """
    Filter organizations by offer.
    """

    offer_id = filters.UUIDFilter(field_name="product_relations__id")

    class Meta:
        model = models.Organization
        fields: List[str] = []
