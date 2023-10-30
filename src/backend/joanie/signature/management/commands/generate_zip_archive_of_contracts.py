"""Management command to generate a zipfile archive of signed contracts into default storage"""
import logging

from django.core.management import BaseCommand, CommandError

from joanie.core import models
from joanie.core.utils import contract as contract_utility

logger = logging.getLogger("joanie.core.generate_zip_archive_of_contracts")


class Command(BaseCommand):
    """
    A command to generate a ZIP archive of contracts that are signed in PDF bytes format.
    It browses all contracts that are signed from a course product relation object through
    the validated orders.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "-cpr",
            "--course_product_relation",
            help=("Accept a single UUID of Course Product Relation object."),
        )

    def handle(self, *args, **options):
        """
        Retrieve all contracts that are signed from a course product relation and return a ZIP
        archive of contracts in bytes.
        """
        if not options["course_product_relation"]:
            logger.error(
                "This is a required parameter `course_product_relation` uuid.",
            )
            raise CommandError(
                "The required parameter `course_product_relation` uuid is missing."
            )

        course_product_relation_uuid = options["course_product_relation"]
        found_course_product_relation = models.CourseProductRelation.objects.filter(
            pk=course_product_relation_uuid
        ).exists()

        if not found_course_product_relation:
            logger.error(
                "Make sure to give an existing course product relation.",
            )
            raise ValueError("Make sure to give an existing course product relation.")

        course_product_relation = models.CourseProductRelation.objects.get(
            pk=course_product_relation_uuid
        )
        signature_references = contract_utility.get_signature_backend_references(
            course_product_relation
        )

        if not signature_references:
            logger.error(
                "There are no signed contracts with the given course product relation object."
            )
            raise ValueError(
                "There are no signed contract attached to the course product relation object."
            )

        pdf_bytes = contract_utility.fetch_pdf_bytes_of_contracts(signature_references)
        zipfile_filename = contract_utility.generate_zipfile(pdf_bytes)

        logger.info(
            (
                "%d contracts were archived in zipfile archive successfully."
                " It can be found in default storage under the filename : %s",
                len(pdf_bytes),
                zipfile_filename,
            ),
        )
