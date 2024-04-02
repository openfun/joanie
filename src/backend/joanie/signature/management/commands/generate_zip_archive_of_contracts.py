"""Management command to generate a ZIP archive of signed contracts into file system storage"""

import logging
import uuid

from django.core.management import BaseCommand, CommandError

from rest_framework.exceptions import ValidationError

from joanie.core import models, serializers
from joanie.core.utils import contract as contract_utility

logger = logging.getLogger("joanie.core.generate_zip_archive_of_contracts")


class Command(BaseCommand):
    """
    This command is exclusive to users who have access rights on a specific organization.
    It generates a ZIP archive of signed contracts of PDF.
    First, you must provide an existing User UUID who has the right access to an organization.
    Then, it gets all signed Contracts from either an existing Course Product Relation object UUID
    or an Organization object UUID.
    If you parse a ZIP UUID into the command parameters, we will use it for the filename, else we
    will generate one in the command
    """

    help = __doc__

    def add_arguments(self, parser):
        """
        The command awaits of 2 required parameters at minimum to be executable.
        First, you should provide an existing User UUID who has the correct access rights to an
        organization, which is primordial. Then, you need to provide either an existing Course
        Product Relation UUID, or an Organization UUID in order to get signed Contracts that are
        attached. You may give a ZIP UUID parameter if you desire, else we generate one for
        the filename.
        """
        parser.add_argument(
            "-usr",
            "--user",
            help=("Accept a single UUID of User object."),
        )

        parser.add_argument(
            "-cpr",
            "--course_product_relation_id",
            help=("Accept a single UUID of Course Product Relation object."),
        )

        parser.add_argument(
            "-org",
            "--organization_id",
            help=("Accept a single UUID of Organization object."),
        )

        parser.add_argument(
            "-z",
            "--zip",
            help=("Accept an 'UUID' like of 36 characters long."),
        )

    def handle(self, *args, **options):
        """
        The command is exclusive to users who have access rights on a specific organization.
        Get all signed contracts from an existing Course Product Relation UUID OR from an
        Organization UUID and generate a ZIP archive into the file system storage.
        """
        zip_uuid = None

        if not (user_id := options["user"]):
            error_message = (
                "You must provide a User UUID for the command because it's required."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)
        serializer = serializers.GenerateSignedContractsZipSerializer(data=options)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as error:
            full_details = error.get_full_details()
            errors = {}
            for name in full_details:
                logger.error(
                    "Error %s: %s", name, str(full_details[name][0]["message"])
                )
                errors[name] = str(full_details[name][0]["message"])
            raise CommandError(errors) from error
        try:
            zip_uuid = uuid.UUID(str(options["zip"]))
        except ValueError:
            zip_uuid = uuid.uuid4()

        if not models.User.objects.filter(pk=user_id).exists():
            error_message = (
                "Make sure to give an existing user UUID. "
                f"No User was found with the given UUID : {user_id}."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        signature_references = contract_utility.get_signature_backend_references(
            course_product_relation=serializer.validated_data.get(
                "course_product_relation"
            ),
            organization=serializer.validated_data.get("organization"),
            extra_filters={"order__organization__accesses__user_id": user_id},
        )  # extra filter to check the access of a user on an organization.

        pdf_bytes = contract_utility.get_pdf_bytes_of_contracts(signature_references)
        if len(pdf_bytes) == 0:
            error_message = (
                "There are no signed contracts with the given parameter. "
                "Abort generating ZIP archive."
            )
            logger.error("Error: %s", error_message)
            raise CommandError(error_message)

        zipfile_filename = contract_utility.generate_zip_archive(
            pdf_bytes_list=pdf_bytes, user_uuid=user_id, zip_uuid=zip_uuid
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
