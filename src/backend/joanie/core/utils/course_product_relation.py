"""Utility methods to get all orders and/or certificates from a course product relation."""

from joanie.core.enums import ORDER_STATE_VALIDATED, PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.models import Certificate, Order


def get_orders(course_product_relation):
    """
    Returns a list of all validated orders ids for a course product relation.
    """
    return [
        str(order_id)
        for order_id in Order.objects.filter(
            course=course_product_relation.course,
            product=course_product_relation.product,
            product__type__in=PRODUCT_TYPE_CERTIFICATE_ALLOWED,
            state=ORDER_STATE_VALIDATED,
            certificate__isnull=True,
        )
        .values_list("pk", flat=True)
        .distinct()
    ]


def get_generated_certificates(course_product_relation):
    """
    Return certificates that were published for a course product relation.
    """
    return Certificate.objects.filter(
        order__product=course_product_relation.product,
        order__course=course_product_relation.course,
        order__certificate__isnull=False,
        order__state=ORDER_STATE_VALIDATED,
    )
