"""
Utility methods for Course Run on enrollments metrics and orders made.
"""

import logging

from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from joanie.core import enums, models

logger = logging.getLogger(__name__)


def get_course_run_metrics(resource_link: str):
    """
    From an existing `resource_link` from an ended Course Run, it returns a dictionary containing :
        - amount of active enrollments,
        - amount of validated certificate orders.
    """
    try:
        course_run = models.CourseRun.objects.get(
            resource_link=resource_link, end__lte=django_timezone.now()
        )
    except models.CourseRun.DoesNotExist as exception:
        error_message = (
            "Make sure to give an existing resource link from an ended course run."
        )
        logger.error("Error: %s", error_message)
        raise ValidationError(error_message) from exception

    return {
        "nb_active_enrollments": models.Enrollment.objects.filter(
            course_run=course_run,
            is_active=True,
        ).count(),
        "nb_validated_certificate_orders": models.Order.objects.filter(
            enrollment__course_run=course_run,
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            state=enums.ORDER_STATE_COMPLETED,
        ).count(),
    }
