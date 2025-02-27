"""Management command to synchronize brevo subscriptions."""

import logging

from django.core.management import BaseCommand

from joanie.core.utils.newsletter.brevo.tasks import synchronize_brevo_subscriptions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to synchronize brevo subscriptions.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Synchronize brevo subscriptions.
        """
        logger.info("Synchronizing brevo subscriptions")
        synchronize_brevo_subscriptions.delay()
