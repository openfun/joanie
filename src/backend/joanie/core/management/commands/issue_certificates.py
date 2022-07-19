"""Management command to generate all pending certificates."""
import logging

from django.core.management import BaseCommand
from django.utils.translation import ngettext_lazy

from joanie.core import models
from joanie.core.helpers import issue_certificates_for_orders

logger = logging.getLogger("joanie.core.issue_certificates")


class Command(BaseCommand):
    """
    A command to issue all pending certificates.
    It browses all certifying products, checks if related orders are eligible for
    certification and issues a certificate if they are.

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
                "Accept a single or a list of product uuid to restrict review to "
                "this/those product(s)."
            ),
        )
        parser.add_argument(
            "-o",
            "--orders",
            "--order",
            help=(
                "Accept a single or a list of order uuid to restrict review to "
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
        order_uids = None
        product_uids = None
        course_codes = None

        if options["orders"]:
            order_uids = (
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
            product_uids = (
                options["products"]
                if isinstance(options["products"], list)
                else [options["products"]]
            )

        filters = {}
        if order_uids:
            filters.update({"uid__in": order_uids})
        else:
            if course_codes:
                filters.update({"course__code__in": course_codes})
            if product_uids:
                filters.update({"product__uid__in": product_uids})

        issued_certificates_count = issue_certificates_for_orders(
            models.Order.objects.filter(**filters)
        )
        logger.info(
            ngettext_lazy(
                "%d certificate has been issued.",
                "%d certificates have been issued.",
                issued_certificates_count,
            ),
            issued_certificates_count,
        )
