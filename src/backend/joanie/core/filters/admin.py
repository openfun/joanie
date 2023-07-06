"""
Admin API Resource Filters
"""
from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from joanie.core import models


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
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    resource_link = filters.CharFilter(
        field_name="resource_link", lookup_expr="icontains"
    )

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()


class CourseAdminFilterSet(filters.FilterSet):
    """
    CourseAdminFilter allows to filter this resource with a query for code and title.
    """

    class Meta:
        model = models.Course
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

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
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for name, title which contains provided value in
        "query" query parameter.
        """

        return queryset.filter(
            Q(name__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


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
