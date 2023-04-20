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

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()

    class Meta:
        model = models.Organization
        fields: List[str] = ["search"]


class ProductAdminFilterSet(filters.FilterSet):
    """
    ProductAdminFilterSet allows to filter this resource with an insensitive search by title.
    """

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in search query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()

    class Meta:
        model = models.Product
        fields: List[str] = ["search"]


class CourseRunAdminFilterSet(filters.FilterSet):
    """
    CourseRunAdminFilter allows to filter this resource with a search title.
    """

    search = filters.CharFilter(method="filter_search")
    resource_link = filters.CharFilter(
        field_name="resource_link", lookup_expr="icontains"
    )

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(translations__title__icontains=value).distinct()

    class Meta:
        model = models.CourseRun
        fields: List[str] = ["search"]


class CourseAdminFilterSet(filters.FilterSet):
    """
    CourseAdminFilter allows to filter this resource with a search for code and title.
    """

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """
        return queryset.filter(
            Q(code__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()

    class Meta:
        model = models.Course
        fields: List[str] = ["search"]


class CertificateDefinitionAdminFilterSet(filters.FilterSet):
    """
    CertificateDefinitionAdminFilter allows to filter this resource with a search
    for name and title.
    """

    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, _name, value):
        """
        construct the full expression for search query param.
        """

        return queryset.filter(
            Q(name__icontains=value) | Q(translations__title__icontains=value)
        ).distinct()

    class Meta:
        model = models.CertificateDefinition
        fields: List[str] = ["search"]
