"""Filters for Skill resource in admin API."""

from django_filters import rest_framework as filters

from joanie.core import models


class SkillAdminFilterSet(filters.FilterSet):
    """
    SkillAdminFilterSet allows to filter this resource
    through a full search text query.
    """

    class Meta:
        model = models.Skill
        fields: list[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(translations__title__icontains=value).distinct()
