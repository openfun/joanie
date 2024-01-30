"""
Admin API Resource Filters
"""
from typing import List

from django.conf import settings
from django.db.models import Q
from django.utils import timezone as django_timezone

from django_filters import rest_framework as filters

from joanie.core import enums, models


class OrganizationAdminFilterSet(filters.FilterSet):
    """
    OrganizationAdminFilter allows to filter this resource with a query for code and title.
    """

    class Meta:
        model = models.Organization
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

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
        fields: List[str] = ["query", "start", "state"]

    query = filters.CharFilter(method="filter_by_query")
    start = filters.IsoDateTimeFilter(field_name="start", lookup_expr="gte")
    state = filters.NumberFilter(method="filter_by_state")

    resource_link = filters.CharFilter(
        field_name="resource_link", lookup_expr="icontains"
    )

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()

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
        )
