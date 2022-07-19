"""
Helpers that can be useful throughout Joanie's core app
"""
from django.core.exceptions import ValidationError
from django.utils import timezone

from joanie.core import enums, models


def issue_certificate_for_order(order):
    """
    Check if order is eligible for certification then issue certificate if it is.

    Eligibility means that order contains
    one passed enrollment per graded courses.

    Return:
        0: if the order is not eligible for certification
        1: if a certificate has been issued for the current order
    """
    graded_courses = (
        order.target_courses.filter(order_relations__is_graded=True)
        .order_by("order_relations__position")
        .prefetch_related("course_runs")
    )
    graded_courses_count = len(graded_courses)

    if graded_courses_count == 0:
        return 0

    # Retrieve all enrollments in one query. Since these enrollments rely on
    # order course runs, the count will always be pretty small.
    course_enrollments = models.Enrollment.objects.filter(
        course_run__course__in=graded_courses,
        course_run__is_gradable=True,
        course_run__start__lte=timezone.now(),
        is_active=True,
        user=order.owner,
    ).select_related("user", "course_run")

    # If we do not have one enrollment per graded course, there is no need to
    # continue, we are sure that order is not eligible for certification.
    if len(course_enrollments) != graded_courses_count:
        return 0

    # Otherwise, we now need to know if each enrollment has been passed
    for enrollment in course_enrollments:
        if enrollment.is_passed is False:
            # If one enrollment has not been passed, no need to continue,
            # We are sure that order is not eligible for certification.
            return 0

    try:
        order.issue_certificate()
    except ValidationError:
        return 0

    return 1


def issue_certificates_for_orders(orders):
    """
    Iterate over the provided orders and check if they are eligible for certification
    then return the count of issued certificates.
    """
    issue_counter = 0

    orders = [
        order
        for order in orders.filter(
            is_canceled=False,
            issued_certificate__isnull=True,
            product__type__in=enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED,
        )
        .select_related("course__organization")
        .iterator()
        if order.state == enums.ORDER_STATE_VALIDATED
    ]

    for order in orders:
        issue_counter += issue_certificate_for_order(order)

    return issue_counter
