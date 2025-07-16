"""Synchronize offerings with the external catalog."""

import logging

from django.core.management import BaseCommand

from joanie.core.utils.offering import synchronize_offerings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to synchronize offerings with the external catalog.
    """

    help = __doc__

    def handle(self, *args, **options):
        """
        Handle the command to synchronize offerings.
        """
        logger.info("Synchronizing offerings")
        synchronize_offerings.delay()
