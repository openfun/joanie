"""Management command to synchronize course runs or equivalent course runs."""

import logging
from uuid import UUID

from django.core.management import BaseCommand
from django.utils.translation import ngettext_lazy

from joanie.core import enums
from joanie.core.models import Course, CourseRun, Product
from joanie.core.utils import webhooks

logger = logging.getLogger("joanie.core.synchronize_course_run")


class Command(BaseCommand):
    """
     A command to trigger course resources (course run or product) synchronization.

     Only listed course runs and credential products can be synchronized. The targeted
     resource(s) are synchronized with each platforms setup through the
     `COURSE_WEB_HOOKS` settings.

    Here is the list of available options:
     --course, -c: a course id or a course code (required)
     --product, -p: a product id or a list of product id.
     --course-run, -cr: a course run id or a list of course run id.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--course",
            "-c",
            help="Accept a single course code or course id (This option is mandatory).",
            required=True,
        )

        parser.add_argument(
            "--course-runs",
            "--course-run",
            "-cr",
            help=(
                "Accept a single course run id or a list of course run id. "
                "Only course runs with flag `is_listed` sets to `True` will be "
                "synchronized. Furthermore, all course runs must be linked to the "
                "provided course."
            ),
        )

        parser.add_argument(
            "--products",
            "--product",
            "-p",
            help=(
                "Accept a single product_id or a list of product_id. "
                "Only products with `type` sets to `CREDENTIAL` will be synchronized. "
                "Furthermore, all products must be linked to the provided course."
            ),
        )

        parser.add_argument(
            "--visibility",
            help=(
                "Enforce the visibility of the course run(s) or product(s) to synchronize. "
                "It accepts all values from `joanie.core.enums.CATALOG_VISIBILITY_CHOICES`. "
                '"course_and_search" - show on the course page and include in search results. '
                '| "course_only" - show on the course page and hide from search results. '
                '| "hidden" - hide on the course page and from search results.'
            ),
        )

    def get_course_filter(self, course_reference: str):
        """
        Return the right lookup filter according to course_reference type is a valid
        UUID or not. If course_reference is a valid UUID, we return a filter on
        `id` else we return a filter on `code`.
        """
        try:
            UUID(course_reference)
        except ValueError:
            lookup_filter = "code"
        else:
            lookup_filter = "id"

        return {lookup_filter: course_reference}

    def get_serialized_course_runs_to_synchronize(
        self, course: Course, course_run_ids: list[str], visibility: str = None
    ) -> list[dict]:
        """
        Return a list of serialized course runs to synchronize.

        If course_run_ids is not provided, all listed course runs linked to the provided
        course will be returned. Otherwise, only listed course runs with ids in
        course_run_ids will be returned.

        If visibility is provided, it will be taken in account during the serialization.
        """
        filters = {"course": course, "is_listed": True}

        if course_run_ids:
            filters["id__in"] = course_run_ids

        return [
            course_run.get_serialized(visibility=visibility)
            for course_run in CourseRun.objects.filter(**filters)
        ]

    def get_serialized_products_to_synchronize(
        self, course: Course, product_ids: list[str] = None, visibility: str = None
    ) -> list[dict]:
        """
        Return a list of serialized products to synchronize.

        If product_ids is not provided, all credential products linked to the provided
        course will be returned. Otherwise, only credential products matching ids in
        product_ids will be returned.

        If visibility is provided, it will be taken in account during the serialization.
        """
        filters = {"type": enums.PRODUCT_TYPE_CREDENTIAL}

        if product_ids:
            filters["id__in"] = product_ids

        return Product.get_equivalent_serialized_course_runs_for_products(
            products=Product.objects.filter(**filters),
            courses=[course],
            visibility=visibility,
        )

    def handle(self, *args, **options):
        """
        Retrieve all synchronizable course runs and/or products according to provided
        options then synchronize them on all platforms setup through the
        `COURSE_WEB_HOOKS` settings.
        """
        course_reference = options["course"]
        course_run_ids = None
        product_ids = None
        visibility = options.get("visibility")

        try:
            filters = self.get_course_filter(course_reference)
            course = Course.objects.get(**filters)
        except Course.DoesNotExist as error:
            filter_key = list(filters.keys())[0]
            raise KeyError(
                f'Course with {filter_key} "{course_reference}" does not exist.'
            ) from error

        if options.get("course_runs"):
            course_run_ids = (
                options["course_runs"]
                if isinstance(options["course_runs"], list)
                else [options["course_runs"]]
            )

        if options.get("products"):
            product_ids = (
                options["products"]
                if isinstance(options["products"], list)
                else [options["products"]]
            )

        serialized_course_runs = []

        if course_run_ids or not product_ids:
            course_runs = self.get_serialized_course_runs_to_synchronize(
                course, course_run_ids, visibility
            )
            serialized_course_runs += course_runs
            logger.info(
                ngettext_lazy(
                    "%d course run to synchronize.",
                    "%d course runs to synchronize.",
                    len(course_runs),
                ),
                len(course_runs),
            )

        if product_ids or not course_run_ids:
            products = self.get_serialized_products_to_synchronize(
                course, product_ids, visibility
            )
            serialized_course_runs += products
            logger.info(
                ngettext_lazy(
                    "%d product to synchronize.",
                    "%d products to synchronize.",
                    len(products),
                ),
                len(products),
            )

        webhooks.synchronize_course_runs(serialized_course_runs)
