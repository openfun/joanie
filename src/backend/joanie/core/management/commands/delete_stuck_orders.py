"""
Management command to delete orders that have been stuck in the `to_sign` or `signing` states
beyond the tolerated time limit.
These stuck orders prevent the release of slots allocated for distributing students
among organizations, particularly when the product is shared across multiple organizations.
By deleteing these orders, we ensure that the slot allocation system remains efficient
and available for other students.
This command also deletes order where the product is type certificate and the state is
in `to_save_payment_method` because that means that the student opened the sales tunnel but
never entered his payment information to purchase the certificate.
"""

import logging

from django.core.management import BaseCommand

from joanie.core.utils.order import delete_stuck_orders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to delete all orders that are stucked in signing states for product with contracts
    and delete all order that are stucked in to save payment method for product of type
    certificate from the database.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Retrieve all orders that are stuck and delete them from the database.
        """
        deleted_orders_in_signing_states, deleted_order_in_to_save_payment_method = (
            delete_stuck_orders()
        )

        logger.info(
            "Deleted %s orders that were stucked in signing states.",
            deleted_orders_in_signing_states,
        )
        logger.info(
            "Deleted %s order that were stucked in to save payment method.",
            deleted_order_in_to_save_payment_method,
        )
