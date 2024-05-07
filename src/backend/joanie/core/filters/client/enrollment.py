"""
Client API Enrollment Filters
"""

from typing import List

from django_filters import rest_framework as filters

from joanie.core import models


class EnrollmentViewSetFilter(filters.FilterSet):
    """
    EnrollmentViewSetFilter allows to filter this resource with a course run id.
    """

    course_run_id = filters.UUIDFilter(field_name="course_run__id")
    was_created_by_order = filters.BooleanFilter(field_name="was_created_by_order")
    query = filters.CharFilter(method="filter_by_query")
    is_active = filters.BooleanFilter()

    class Meta:
        model = models.Enrollment
        fields: List[str] = []

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for course title
        """
        return queryset.filter(
            course_run__course__translations__title__icontains=value
        ).distinct()
