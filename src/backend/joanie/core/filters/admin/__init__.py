"""
Admin API Resource Filters
"""

from typing import List

from django.conf import settings
from django.db.models import Q
from django.forms import fields
from django.utils import timezone as django_timezone

from django_filters import rest_framework as filters

from joanie.core import enums, models
from joanie.core.filters.base import MultipleValueFilter
from joanie.core.utils import get_default_currency_symbol

from .enrollment import EnrollmentAdminFilterSet
from .skill import SkillAdminFilterSet
from .teacher import TeacherAdminFilterSet


class OrganizationAdminFilterSet(filters.FilterSet):
    """
    OrganizationAdminFilter allows to filter this resource with a query for code and title.
    """

    class Meta:
        model = models.Organization
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter the resource through "query" query parameter.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class ProductAdminFilterSet(filters.FilterSet):
    """
    ProductAdminFilterSet allows to filter this resource with an insensitive query by title.
    """

    class Meta:
        model = models.Product
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    type = filters.ChoiceFilter(choices=enums.PRODUCT_TYPE_CHOICES)
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()


class CourseRunAdminFilterSet(filters.FilterSet):
    """
    CourseRunAdminFilter allows to filter this resource with a query title.
    """

    class Meta:
        model = models.CourseRun
        fields: List[str] = ["query", "state"]

    query = filters.CharFilter(method="filter_by_query")
    start = filters.IsoDateTimeFilter(field_name="start", lookup_expr="gte")
    state = filters.NumberFilter(method="filter_by_state")
    course_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Course.objects.all().only("pk"),
        field_name="course",
        distinct=True,
    )
    organization_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Organization.objects.all().only("pk"),
        field_name="course__organizations",
        distinct=True,
    )
    is_gradable = filters.BooleanFilter()
    is_listed = filters.BooleanFilter()
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(
            Q(translations__title__icontains=value) | Q(resource_link__icontains=value)
        ).distinct()

    def filter_by_state(self, queryset, _name, value):
        """
        Filter resource by looking for states that match the one provided
        in the "state" parameter
        """
        now = django_timezone.now()
        if value == models.CourseState.ONGOING_OPEN:
            queryset = queryset.filter(
                start__lte=now,
                end__gt=now,
                enrollment_start__lte=now,
                enrollment_end__gt=now,
            )
        elif value == models.CourseState.FUTURE_OPEN:
            queryset = queryset.filter(
                start__gt=now, enrollment_start__lte=now, enrollment_end__gt=now
            )
        elif value == models.CourseState.ARCHIVED_OPEN:
            queryset = queryset.filter(
                end__lte=now,
                enrollment_start__lte=now,
                enrollment_end__gt=now,
            )
        elif value == models.CourseState.FUTURE_NOT_YET_OPEN:
            queryset = queryset.filter(
                start__gt=now,
                enrollment_start__gt=now,
            )
        elif value == models.CourseState.FUTURE_CLOSED:
            queryset = queryset.filter(start__gt=now, enrollment_end__lte=now)
        elif value == models.CourseState.ONGOING_CLOSED:
            queryset = queryset.filter(
                Q(enrollment_end__lte=now) | Q(enrollment_start__gt=now),
                start__lte=now,
                end__gt=now,
            )
        elif value == models.CourseState.ARCHIVED_CLOSED:
            queryset = queryset.filter(
                Q(enrollment_end__lte=now) | Q(enrollment_start__gt=now),
                end__lte=now,
            )
        elif value == models.CourseState.TO_BE_SCHEDULED:
            queryset = queryset.filter(
                Q(start__isnull=True) | Q(enrollment_start__isnull=True)
            )
        elif value != "":
            queryset = queryset.none()
        return queryset


class CourseAdminFilterSet(filters.FilterSet):
    """
    CourseAdminFilter allows to filter this resource with a query for code and title.
    """

    class Meta:
        model = models.Course
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    organization_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Organization.objects.all().only("pk"),
        field_name="organizations",
        distinct=True,
    )
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for code, title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class CertificateDefinitionAdminFilterSet(filters.FilterSet):
    """
    CertificateDefinitionAdminFilter allows to filter this resource with a query
    for name and title.
    """

    class Meta:
        model = models.CertificateDefinition
        fields: List[str] = ["query", "template"]

    query = filters.CharFilter(method="filter_by_query")
    template = filters.ChoiceFilter(choices=enums.CERTIFICATE_NAME_CHOICES)
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for name, title which contains provided value in
        "query" query parameter.
        """

        return queryset.filter(
            Q(name__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class ContractDefinitionAdminFilterSet(filters.FilterSet):
    """
    ContractDefinitionAdminFilter allows to filter this resource with a query
    for name and title.
    """

    class Meta:
        model = models.ContractDefinition
        fields: List[str] = ["query", "language"]

    query = filters.CharFilter(method="filter_by_query")
    language = filters.ChoiceFilter(choices=settings.LANGUAGES)
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """

        return queryset.filter(title__icontains=value).distinct()


class UserAdminFilterSet(filters.FilterSet):
    """
    UserAdminFilter allows to filter this resource with a query for username,
    first name, last name and email.
    """

    query = filters.CharFilter(method="filter_by_query")
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for username, first_name, last_name and email which
        contains provided value in "query" query parameter.
        """

        return queryset.filter(
            Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(email__icontains=value)
        ).distinct()


class OrderAdminFilterSet(filters.FilterSet):
    """
    FilterSet to filter orders by several criteria.
    """

    class Meta:
        model = models.Order
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    course_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Course.objects.all().only("pk"),
        field_name="course",
        distinct=True,
    )
    organization_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Organization.objects.all().only("pk"),
        field_name="organization",
        distinct=True,
    )
    owner_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.User.objects.all().only("pk"),
        field_name="owner",
        distinct=True,
    )
    product_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.Product.objects.all().only("pk"),
        field_name="product",
        distinct=True,
    )
    state = filters.ChoiceFilter(choices=enums.ORDER_STATE_CHOICES)
    ids = MultipleValueFilter(field_class=fields.UUIDField, field_name="id")
    product_type = filters.MultipleChoiceFilter(
        field_name="product__type",
        choices=enums.PRODUCT_TYPE_CHOICES,
    )
    created_on = filters.DateFilter(field_name="created_on", lookup_expr="date")
    created_on_date_range = filters.DateFromToRangeFilter(field_name="created_on")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for product title, course title | code, organization
        title | code, owner username, email, full_name
        """

        return queryset.filter(
            Q(course__translations__title__icontains=value)
            | Q(course__code__icontains=value)
            | Q(organization__translations__title__icontains=value)
            | Q(organization__code__icontains=value)
            | Q(product__translations__title__icontains=value)
            | Q(owner__email__icontains=value)
            | Q(owner__username__icontains=value)
            | Q(owner__first_name__icontains=value)
            | Q(owner__last_name__icontains=value)
        ).distinct()


class DiscountAdminFilterSet(filters.FilterSet):
    """
    DiscountAdminFilterSet allows to filter this resource with a query for amount and rate.
    """

    class Meta:
        model = models.Discount
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for amount and rate which contains provided value in
        "query" query parameter.
        """

        def amount_filter(amount, exact=False):
            if exact and amount:
                return Q(amount=amount)
            return Q(amount__icontains=amount)

        def rate_filter(rate, exact=False):
            try:
                rate = int(rate) / 100
            except ValueError:
                pass

            if exact and rate:
                return Q(rate=rate)
            return Q(rate__icontains=rate)

        currency_symbol = get_default_currency_symbol()
        if currency_symbol in value:
            value = value.replace(currency_symbol, "")
            queryset = queryset.filter(amount_filter(value, exact=True))
        elif "%" in value:
            value = value.replace("%", "")
            queryset = queryset.filter(rate_filter(value, exact=True))
        else:
            queryset = queryset.filter(amount_filter(value) | rate_filter(value))

        return queryset.distinct()
