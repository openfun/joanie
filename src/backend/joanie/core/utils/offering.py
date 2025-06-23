"""Utility methods to get all orders and/or certificates from an offering."""

from django.db.models import Q

from joanie.core.enums import ORDER_STATE_COMPLETED, PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.models import Certificate, Order


def get_orders(offering):
    """
    Returns a list of all completed orders ids for an offering.
    """
    return [
        str(order_id)
        for order_id in Order.objects.filter(
            Q(course=offering.course, enrollment__isnull=True)
            | Q(
                course__isnull=True,
                enrollment__course_run__course=offering.course,
            ),
            product=offering.product,
            product__type__in=PRODUCT_TYPE_CERTIFICATE_ALLOWED,
            state=ORDER_STATE_COMPLETED,
            certificate__isnull=True,
        )
        .values_list("pk", flat=True)
        .distinct()
    ]


def get_generated_certificates(offering):
    """
    Return certificates that were published for an offering.
    """
    return Certificate.objects.filter(
        Q(order__course=offering.course, order__enrollment__isnull=True)
        | Q(
            order__course__isnull=True,
            order__enrollment__course_run__course=offering.course,
        ),
        order__product=offering.product,
        order__certificate__isnull=False,
        order__state=ORDER_STATE_COMPLETED,
    )
