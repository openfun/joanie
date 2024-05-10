"""Management command to process all pending payment schedules."""

import logging

from django.core.management import BaseCommand

from joanie.core.models import Order
from joanie.core.tasks.payment_schedule import process_today_installment

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
        found_orders = Order.objects.find_today_installments()
        if not found_orders:
            logger.info("No pending payment schedule found.")
            return

        logger.info("Found %s pending payment schedules.", len(found_orders))
        for order in found_orders:
            logger.info("Processing payment schedule for order %s.", order.id)
            process_today_installment.delay(order.id)
