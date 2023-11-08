"""Management command to generate a ZIP archive of signed contracts into file system storage"""
import logging
from uuid import uuid4

from django.core.management import BaseCommand, CommandError

from joanie.core import models
from joanie.core.utils import contract as contract_utility

logger = logging.getLogger("joanie.core.generate_zip_archive_of_contracts")


class Command(BaseCommand):
    """
    A command to generate a ZIP archive of signed contracts in PDF bytes format.
    You must provide first an existing User UUID. Then, it browses all signed Contracts from
    either a Course Product Relation object UUID or an Organization object UUID.
    If you parse a ZIP UUID, we can use it for the filename, else we generate one in the command.
    """

    help = __doc__

    def add_arguments(self, parser):
        """
        For this command, we await 2 parameters in minimum to be executable.
        First, you should provide an existing User UUID, which is primordial.
        Then, you may use an existing Course Product Relation UUID, or an Organization UUID in
        order to fetch signed Contracts attached to the given object.
        You may give a ZIP UUID if you desire, else we generate one for the filename.
        """
        parser.add_argument(
            "-usr",
            "--user",
            help=("Accept a single UUID of User object."),
        )

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

        parser.add_argument(
            "-z",
            "--zip",
            help=("Accept an 'UUID' like of 36 characters long."),
        )

    def handle(self, *args, **options):
        """
        Fetch all signed contracts from a Course Product Relation UUID OR from an Organization UUID
        and generate a ZIP archive into the file system storage that is located at
        `data/contracts`.
        """
        course_product_relation = None
        organization = None
        user_uuid = None

        if not options["user"]:
            error_message = (
                "You must provide a User UUID for the command because it's required."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        if not options["organization"] and not options["course_product_relation"]:
            error_message = (
                "You must to provide at least one of the two required parameters. "
                "It can be a Course Product Relation UUID, or an Organization UUID."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        # UUID version 4 is 36 characters of numbers and standard alphabetic letters long
        zip_uuid = (
            str(options["zip"]).replace("_", "-")
            if options["zip"] is not None and len(str(options["zip"])) <= 36
            else uuid4()
        )

        if user_uuid := options["user"]:
            try:
                models.User.objects.filter(pk=user_uuid).exists()
            except models.User.DoesNotExist as error:
                error_message = (
                    "Make sure to give an existing user UUID. "
                    f"No User was found with the given UUID : {user_uuid}."
                )
                logger.error("Error: %s", error_message)
                raise CommandError(error) from error

        if course_product_relation_uuid := options["course_product_relation"]:
            try:
                course_product_relation = models.CourseProductRelation.objects.get(
                    pk=course_product_relation_uuid
                )
            except models.CourseProductRelation.DoesNotExist as error:
                error_message = (
                    "Make sure to give an existing course product relation UUID. "
                    "No CourseProductRelation was found with the given "
                    f"UUID : {course_product_relation_uuid}."
                )
                logger.error("Error: %s", error_message)
                raise CommandError(error_message) from error

        if organization_uuid := options["organization"]:
            try:
                organization = models.Organization.objects.get(pk=organization_uuid)
            except models.Organization.DoesNotExist as error:
                error_message = (
                    "Make sure to give an existing organization UUID. "
                    f"No Organization was found with the givin UUID : {organization_uuid}."
                )
                logger.error("Error: %s", error_message)
                raise CommandError(error_message) from error

        signature_references = contract_utility.get_signature_backend_references(
            course_product_relation=course_product_relation, organization=organization
        )

        pdf_bytes = contract_utility.fetch_pdf_bytes_of_contracts(signature_references)
        if len(pdf_bytes) == 0:
            error_message = (
                "There are no signed contracts with the given parameter. "
                "Abort generating ZIP archive."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        zipfile_filename = contract_utility.generate_zipfile(
            pdf_bytes_list=pdf_bytes, user_uuid=user_uuid, zip_uuid=zip_uuid
        )

        logger.info(
            (
                "%d contracts were archived in ZIP archive successfully."
                " It can be found in File System Storage under the filename : %s",
                len(pdf_bytes),
                zipfile_filename,
            ),
        )

        self.stdout.write(self.style.SUCCESS(f"{zipfile_filename}"))
