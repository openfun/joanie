"""Utility methods to get all orders and/or certificates from an offering."""

from django.db.models import Q

from joanie.core import enums
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


def get_serialized_course_runs(offering):
    """
    Synchronize course runs related to an offering.
    """
    product = offering.product
    course = offering.course
    course_runs = course.course_runs.all()
    serialized_course_runs = []
    for course_run in course_runs:
        certifying = product.type == enums.PRODUCT_TYPE_CERTIFICATE
        if serialized_runs := course_run.get_serialized(
            certifying=certifying, product=product
        ):
            serialized_course_runs.append(serialized_runs)

        if (
            serialized_runs
            := course_run.get_equivalent_serialized_course_runs_for_related_products()
        ):
            serialized_course_runs.extend(serialized_runs)

    if serialized_course_runs:
        return serialized_course_runs

    return None
