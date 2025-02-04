"""Management command to clean up all unused credit cards."""

import logging

from django.core.management import BaseCommand

from joanie.payment.models import CreditCard

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to clean up all unused credit cards.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Delete all unused credit cards.
        """
        unlinked_credit_cards, deleted_credit_cards = CreditCard.objects.delete_unused()

        logger.info("Unlinked %s credit cards:", len(unlinked_credit_cards))
        for unlinked_credit_card in unlinked_credit_cards:
            logger.info("  %s", unlinked_credit_card["order_id"])

        logger.info("Deleted %s credit cards:", len(deleted_credit_cards))
        for deleted_credit_card in deleted_credit_cards:
            logger.info("  %s", deleted_credit_card["card_id"])
