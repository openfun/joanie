"""Utility methods to get all orders and/or certificates from an offer."""

from django.db.models import Q

from joanie.core.enums import ORDER_STATE_COMPLETED, PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.models import Certificate, Order


def get_orders(offer):
    """
    Returns a list of all completed orders ids for an offer.
    """
    return [
        str(order_id)
        for order_id in Order.objects.filter(
            Q(course=offer.course, enrollment__isnull=True)
            | Q(
                course__isnull=True,
                enrollment__course_run__course=offer.course,
            ),
            product=offer.product,
            product__type__in=PRODUCT_TYPE_CERTIFICATE_ALLOWED,
            state=ORDER_STATE_COMPLETED,
            certificate__isnull=True,
        )
        .values_list("pk", flat=True)
        .distinct()
    ]


def get_generated_certificates(offer):
    """
    Return certificates that were published for an offer.
    """
    return Certificate.objects.filter(
        Q(order__course=offer.course, order__enrollment__isnull=True)
        | Q(
            order__course__isnull=True,
            order__enrollment__course_run__course=offer.course,
        ),
        order__product=offer.product,
        order__certificate__isnull=False,
        order__state=ORDER_STATE_COMPLETED,
    )
