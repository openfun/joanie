"""Utility methods to get all orders and/or certificates from a course product relation."""

from django.db.models import Q

from joanie.core.enums import ORDER_STATE_COMPLETED, PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.models import Certificate, Order


def get_orders(course_product_relation):
    """
    Returns a list of all completed orders ids for a course product relation.
    """
    return [
        str(order_id)
        for order_id in Order.objects.filter(
            Q(course=course_product_relation.course, enrollment__isnull=True)
            | Q(
                course__isnull=True,
                enrollment__course_run__course=course_product_relation.course,
            ),
            product=course_product_relation.product,
            product__type__in=PRODUCT_TYPE_CERTIFICATE_ALLOWED,
            state=ORDER_STATE_COMPLETED,
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
        Q(order__course=course_product_relation.course, order__enrollment__isnull=True)
        | Q(
            order__course__isnull=True,
            order__enrollment__course_run__course=course_product_relation.course,
        ),
        order__product=course_product_relation.product,
        order__certificate__isnull=False,
        order__state=ORDER_STATE_COMPLETED,
    )
