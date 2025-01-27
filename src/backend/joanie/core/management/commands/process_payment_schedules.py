"""Management command to process all pending payment schedules."""

import logging

from django.core.management import BaseCommand

from joanie.core.models import Order
from joanie.core.tasks.payment_schedule import debit_pending_installment
from joanie.core.utils.payment_schedule import has_installments_to_debit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to process all pending payment schedules.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Retrieve all pending payment schedules and process them.
        """
        logger.info("Starting processing of all pending payment schedules.")
        found_orders_count = 0

        for order in Order.objects.find_installments_to_pay().iterator():
            if has_installments_to_debit(order):
                logger.info("Processing payment schedule for order %s.", order.id)
                debit_pending_installment.delay(order.id)
                found_orders_count += 1

        logger.info("Found %s pending payment schedules.", found_orders_count)
