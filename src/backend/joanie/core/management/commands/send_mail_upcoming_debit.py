"""Management command to send a reminder email to the order's owner on next installment to pay"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone

from joanie.core.models import Order
from joanie.core.tasks.payment_schedule import send_mail_reminder_installment_debit_task
from joanie.core.utils.payment_schedule import is_next_installment_to_debit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command to send an email to the order's owner notifying them that an upcoming
    installment debit from their payment schedule will be debited soon on their credit card.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Retrieve all upcoming pending payment schedules depending on the target due date and
        send an email reminder to the order's owner who will be soon debited.
        """
        logger.info(
            "Starting processing order payment schedule for upcoming installments."
        )
        due_date = timezone.localdate() + timedelta(
            days=settings.JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS
        )

        found_orders_count = 0
        for order in Order.objects.find_pending_installments().iterator():
            for installment in order.payment_schedule:
                if is_next_installment_to_debit(
                    installment=installment, due_date=due_date
                ):
                    logger.info("Sending reminder mail for order %s.", order.id)
                    send_mail_reminder_installment_debit_task.delay(
                        order_id=order.id, installment_id=installment["id"]
                    )
            found_orders_count += 1

        logger.info(
            "Found %s upcoming 'pending' installment to debit",
            found_orders_count,
        )
