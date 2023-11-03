"""Management command to generate a zipfile archive of signed contracts into default storage"""
import logging

from django.core.management import BaseCommand, CommandError

from joanie.core import models
from joanie.core.utils import contract as contract_utility

logger = logging.getLogger("joanie.core.generate_zip_archive_of_contracts")


class Command(BaseCommand):
    """
    A command to generate a ZIP archive of contracts that are signed in PDF bytes format.
    It browses all signed contracts from either a course product relation object UUID or
    an Organization object UUID.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "-cpr",
            "--course_product_relation",
            help=("Accept a single UUID of Course Product Relation object."),
        )

        parser.add_argument(
            "-org",
            "--organization",
            help=("Accept a single UUID of Organization object."),
        )

    def handle(self, *args, **options):
        """
        Retrieve all contracts that are signed from a course product relation or from
        an organization and return a ZIP archive of the contracts in bytes.
        """
        course_product_relation = None
        organization = None

        if not options["organization"] and not options["course_product_relation"]:
            error_message = (
                "You need to provide at least one of the two required parameters. "
                "It can be a Course Product Relation UUID, or an Organization UUID."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        if options["course_product_relation"]:
            course_product_relation_uuid = (
                options["course_product_relation"]
                if isinstance(options["course_product_relation"], str)
                else str(options["course_product_relation"])
            )
            try:
                course_product_relation = models.CourseProductRelation.objects.get(
                    pk=course_product_relation_uuid
                )
            except models.CourseProductRelation.DoesNotExist as error:
                error_message = (
                    "Make sure to give an existing course product relation uuid. "
                    "No CourseProductRelation was found with the given "
                    f"UUID : {course_product_relation_uuid}."
                )
                logger.error("Error: %s", error_message)
                raise CommandError(error_message) from error

        if options["organization"]:
            organization_uuid = (
                options["organization"]
                if isinstance(options["organization"], str)
                else str(options["organization"])
            )
            try:
                organization = models.Organization.objects.get(pk=organization_uuid)
            except models.Organization.DoesNotExist as error:
                error_message = (
                    "Make sure to give an existing organization uuid. "
                    f"No Organization was found with the givin UUID : {organization_uuid}."
                )
                logger.error("Error: %s", error_message)
                raise CommandError(error_message) from error

        signature_references = contract_utility.get_signature_backend_references(
            course_product_relation=course_product_relation, organization=organization
        )

        if not signature_references:
            error_message = (
                "There are no signed contracts with the given parameter. "
                "Abort generating ZIP archive."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

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
