"""Utility to get all validated orders from a course product relation object."""

from joanie.core.enums import ORDER_STATE_VALIDATED
from joanie.core.models import Order


def get_orders(course_product_relation):
    """
    Utility method that returns a list of all validated orders ids from a course product
    relation object.
    """
    return [
        str(order_id)
        for order_id in Order.objects.filter(
            course=course_product_relation.course,
            product=course_product_relation.product,
            state=ORDER_STATE_VALIDATED,
        )
        .values_list("pk", flat=True)
        .distinct()
    ]
