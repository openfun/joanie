"""
Admin Enrollment API Resource Filters
"""

from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from joanie.core import enums, models


class EnrollmentAdminFilterSet(filters.FilterSet):
    """
    EnrollmentAdminFilterSet allows to filter this resource
    through a full search text query, course_run_ids, user_ids, ids, active state
    and state.
    """

    class Meta:
        model = models.Enrollment
        fields: List[str] = ["query"]

    query = filters.CharFilter(method="filter_by_query")
    course_run_ids = filters.ModelMultipleChoiceFilter(
        queryset=models.CourseRun.objects.all().only("pk"),
        field_name="course_run",
        distinct=True,
    )

    def filter_by_query(self, queryset, _name, value):
        """
        Filter resource by looking for title which contains provided value in
        "query" query parameter.
        """
        return queryset.filter(
            Q(course_run__translations__title__icontains=value)
            | Q(course_run__resource_link__icontains=value)
            | Q(course_run__course__code__icontains=value)
        ).distinct()
