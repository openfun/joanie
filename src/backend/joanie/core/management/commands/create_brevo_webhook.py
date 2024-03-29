"""Management command to create a brevo webhook."""

import logging

from django.core.management import BaseCommand

from joanie.core.utils.newsletter.brevo import Brevo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A command to create a brevo webhook.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            help="The base URL of the webhook.",
            required=True,
        )
        parser.add_argument(
            "--description",
            help="The description of the webhook.",
            required=False,
        )

    def handle(self, *args, **options):
        """
        Create a brevo webhook.
        """
        base_url = options["base_url"]
        description = options.get("description")
        logger.info("Creating brevo webhook at %s", base_url)
        Brevo().create_webhook(base_url, description)
