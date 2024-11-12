"""Filters for Teacher resource in admin API."""

from django.db.models import Value
from django.db.models.functions import Concat

from django_filters import rest_framework as filters

from joanie.core import models


class TeacherAdminFilterSet(filters.FilterSet):
    """
    TeacherAdminFilterSet allows to filter this resource
    through a full search text query.
    """

    class Meta:
        model = models.Teacher
        fields: list[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """

        return queryset.annotate(
            full_name=Concat("first_name", Value(" "), "last_name")
        ).filter(full_name__icontains=value)
