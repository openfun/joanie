"""
Admin API Resource Filters
"""
from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from joanie.core import models


class OrganizationAdminFilterSet(filters.FilterSet):
    """
    OrganizationAdminFilter allows to filter this resource with a search for code and title.
    """

    class Meta:
        model = models.Organization
        fields: List[str] = ["search"]

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class ProductAdminFilterSet(filters.FilterSet):
    """
    ProductAdminFilterSet allows to filter this resource with an insensitive search by title.
    """

    class Meta:
        model = models.Product
        fields: List[str] = ["search"]

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in search
        query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()


class CourseRunAdminFilterSet(filters.FilterSet):
    """
    CourseRunAdminFilter allows to filter this resource with a search title.
    """

    class Meta:
        model = models.CourseRun
        fields: List[str] = ["search"]

    search = filters.CharFilter(method="filter_search")
    resource_link = filters.CharFilter(
        field_name="resource_link", lookup_expr="icontains"
    )

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(translations__title__icontains=value).distinct()


class CourseAdminFilterSet(filters.FilterSet):
    """
    CourseAdminFilter allows to filter this resource with a search for code and title.
    """

    class Meta:
        model = models.Course
        fields: List[str] = ["search"]

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class CertificateDefinitionAdminFilterSet(filters.FilterSet):
    """
    CertificateDefinitionAdminFilter allows to filter this resource with a search
    for name and title.
    """

    class Meta:
        model = models.CertificateDefinition
        fields: List[str] = ["search"]

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """

        return queryset.filter(
            Q(name__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()


class UserAdminFilterSet(filters.FilterSet):
    """
    UserAdminFilter allows to filter this resource with a search for username,
    first name, last name and email.
    """

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        Construct the full expression for search query param.
        """

        return queryset.filter(
            Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(email__icontains=value)
        )
