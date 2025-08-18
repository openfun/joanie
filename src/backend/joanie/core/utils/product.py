"""Util to manage the synchronization of course runs related to a product."""

import logging

from joanie.core import enums
from joanie.core.utils import webhooks

logger = logging.getLogger(__name__)


def synchronize_product_course_runs(product):
    """
    Synchronize course runs related to the product.
    """
    if product.type == enums.PRODUCT_TYPE_CERTIFICATE:
        serialized_course_runs = product.get_serialized_certificated_course_runs(
            [product]
        )
        logger.debug(serialized_course_runs)
    else:
        serialized_course_runs = (
            product.get_equivalent_serialized_course_runs_for_products([product])
        )
        logger.debug(serialized_course_runs)

    if serialized_course_runs:
        webhooks.synchronize_course_runs(serialized_course_runs)
