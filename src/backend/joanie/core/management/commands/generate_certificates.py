"""Management command to generate all pending certificates."""
import logging

from django.core.management import BaseCommand
from django.utils.translation import ngettext_lazy

from joanie.core import models
from joanie.core.helpers import generate_certificates_for_orders

logger = logging.getLogger("joanie.core.generate_certificates")


class Command(BaseCommand):
    """
    A command to generate all pending certificates.
    It browses all certifying products, checks if related orders are eligible for
    certification and generates a certificate if they are.

    Through options, you are able to restrict this command
    to a list of courses (-c), products (-p) or orders (-o).
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--courses",
            "--course",
            help=(
                "Accept a single or a list of course code to restrict review to "
                "this/those course(s)."
            ),
        )
        parser.add_argument(
            "-p",
            "--products",
            "--product",
            help=(
                "Accept a single or a list of product id to restrict review to "
                "this/those product(s)."
            ),
        )
        parser.add_argument(
            "-o",
            "--orders",
            "--order",
            help=(
                "Accept a single or a list of order id to restrict review to "
                "this/those order(s)."
            ),
        )

    # pylint: disable=too-many-locals
    def handle(self, *args, **options):
        """
        Retrieve all certifying products then for each of them check eligibility for
        certification of all related orders.
        If `order` option is used, this order is directly retrieved.
        """
        order_ids = None
        product_ids = None
        course_codes = None

        if options["orders"]:
            order_ids = (
                options["orders"]
                if isinstance(options["orders"], list)
                else [options["orders"]]
            )

        if options["courses"]:
            course_codes = (
                options["courses"]
                if isinstance(options["courses"], list)
                else [options["courses"]]
            )

        if options["products"]:
            product_ids = (
                options["products"]
                if isinstance(options["products"], list)
                else [options["products"]]
            )

        filters = {}
        if order_ids:
            filters.update({"id__in": order_ids})
        else:
            if course_codes:
                filters.update({"course__code__in": course_codes})
            if product_ids:
                filters.update({"product__id__in": product_ids})

        certificate_generated_count = generate_certificates_for_orders(
            models.Order.objects.filter(**filters)
        )
        logger.info(
            ngettext_lazy(
                "%d certificate has been generated.",
                "%d certificates have been generated.",
                certificate_generated_count,
            ),
            certificate_generated_count,
        )
