"""
Utility methods for Course Run to aggregate dates from a course run queryset.
"""

from django.db import models as django_models
from django.utils import timezone as django_timezone


def aggregate_course_runs_dates(
    course_runs: django_models.QuerySet, ignore_archived: bool = False
):
    """
    Return a dict of dates equivalent to course run dates
    by aggregating dates of all course runs as follows:
    - start: Pick the earliest start date
    - end: Pick the latest end date
    - enrollment_start: Pick the latest enrollment start date
    - enrollment_end: Pick the earliest enrollment end date

    It is possible to ignore archived course runs by setting ignore_archived to True.
    """

    qs = course_runs

    if ignore_archived:
        qs = course_runs.filter(end__gt=django_timezone.now())

    aggregate = qs.aggregate(
        django_models.Min("start"),
        django_models.Max("end"),
        django_models.Max("enrollment_start"),
        django_models.Min("enrollment_end"),
    )

    return {key.split("__")[0]: value for key, value in aggregate.items()}
