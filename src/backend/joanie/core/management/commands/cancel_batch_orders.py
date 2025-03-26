"""
Management command to cancel batch order where the payment was not fixed within the
tolerated time limit setting.
"""

import logging

from django.core.management import BaseCommand

from joanie.core.models import BatchOrder
from joanie.core.utils.batch_order import cancel_batch_orders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to cancel batch order because the payment is still in failure after
    the tolerated time limit setted in settings.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Retrieve all batch orders that are stuck in failed payment and cancel them.
        """

        canceled_batch_order_count = cancel_batch_orders()

        logger.info(
            "Canceled %s batch orders that was stucked in failed payment states.",
            canceled_batch_order_count,
        )
