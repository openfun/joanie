"""Utility methods to get all orders and/or certificates from an offering."""

import logging
import secrets

from django.db.models import Q

from joanie.celery_app import app
from joanie.core import enums
from joanie.core.enums import ORDER_STATE_COMPLETED, PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.models import Certificate, CourseProductRelation, OfferingRule, Order
from joanie.core.utils import webhooks

logger = logging.getLogger(__name__)


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


def get_deep_link(offering) -> str | None:
    """
    Return a random active deep link for the given offering.

    If the offering does not have deep links enabled or none were declared,
    returns None. Otherwise, it selects and returns one of the active deep links
    associated with the offering
    """
    if not offering.has_deep_links or not offering.can_access_deep_links:
        return None

    activated_deep_links = list(
        offering.organization_links.filter(is_active=True).values_list(
            "deep_link", flat=True
        )
    )
    return secrets.choice(activated_deep_links)


def get_serialized_course_runs(offering, visibility=None):
    """
    Serialize the course runs to synchronize for an offering.

    A credential/other product is synchronized as one single equivalent course run
    (the same one the "Product" signals send), otherwise each course run of the
    course would overwrite the previous one in the remote catalog as they all
    share the offering uri as resource link.
    """
    product = offering.product
    course_run_data = product.get_equivalent_course_run_data(
        visibility=visibility, ignore_archived=True
    )
    if course_run_data is not None:
        if not any(
            course_run_data[k]
            for k in ("start", "end", "enrollment_start", "enrollment_end")
        ):
            return None
        rules = offering.rules
        return [
            {
                **course_run_data,
                "resource_link": offering.uri,
                "course": offering.course.code,
                "discounted_price": rules.get("discounted_price"),
                "discount": rules.get("discount"),
            }
        ]

    # Certificate products are synchronized with one course run per course run
    serialized_course_runs = []
    for course_run in offering.course.course_runs.all():
        if course_run.is_archived:
            continue
        if serialized_runs := course_run.get_serialized(
            visibility=visibility, certifying=True, product=product
        ):
            logger.debug("[SYNC] %s", serialized_runs)
            serialized_course_runs.append(serialized_runs)

    return serialized_course_runs or None


@app.task
def synchronize_offerings():
    """
    Synchronize all offerings that have rules to synchronize.
    """
    offering_ids = (
        OfferingRule.objects.find_to_synchronize()
        .values_list("course_product_relation", flat=True)
        .distinct()
    )

    offerings = (
        CourseProductRelation.objects.filter(
            id__in=offering_ids,
        )
        .select_related("course", "product")
        .distinct()
    )

    logger.info("Synchronizing %s offerings", offerings.count())

    course_runs = []
    for offering in offerings:
        logger.info("Get serialized course runs for offering %s", offering.id)
        visibility = None
        if offering.product.type == enums.PRODUCT_TYPE_CREDENTIAL:
            visibility = enums.COURSE_AND_SEARCH
        synchronized_course_runs = get_serialized_course_runs(
            offering, visibility=visibility
        )
        if synchronized_course_runs:
            logger.info(
                "  %s course runs serialized",
                len(synchronized_course_runs),
            )
            course_runs.extend(synchronized_course_runs)
        else:
            logger.info("  No course runs serialized")

    if course_runs:
        logger.info("Synchronizing %s course runs for offerings", len(course_runs))
        webhooks.synchronize_course_runs(course_runs)
