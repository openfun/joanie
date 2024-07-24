"""populate_certificate_signatory command module"""

import logging

from django.core.management import BaseCommand

from joanie.edx_imports.checks import (
    check_import_db_connections,
    check_import_env,
    check_openedx_host,
)
from joanie.edx_imports.tasks import populate_signatory_certificates_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Retrieve certificate without signatory then try to populate missing signatory"""

    def add_arguments(self, parser):
        """Add arguments to the command"""
        parser.add_argument(
            "--skip-check",
            action="store_true",
            default=False,
            help="Skip check the env vars and db connections",
        )
        parser.add_argument(
            "--id",
            type=str,
            help="To populate signatory for a specific certificate",
        )
        parser.add_argument(
            "--course-id",
            type=str,
            help="To populate signatory for all certificates of a specific course",
        )

    def handle(self, *args, **options):
        """Handle the command"""

        skip_check = options.get("skip_check")
        certificate_id = options.get("id")
        course_id = options.get("course_id")

        if not skip_check:
            logger.info("Checking the environment and database connections...")
            check_result = check_import_env(self.style)
            check_result = check_openedx_host(self.style) and check_result
            check_result = check_import_db_connections(self.style) and check_result
            if not check_result:
                logger.error(self.style.ERROR("\nCheck failed"))
                continue_import = input(
                    "\nDo you want to continue importing data? (yes/no): "
                )
                if continue_import.lower() not in ["yes", "y"]:
                    return
                logger.warning(
                    self.style.WARNING("Continuing import despite failed checks")
                )

        populate_signatory_certificates_task.delay(
            certificate_id=certificate_id, course_id=course_id
        )

        logger.info("Populate signatory certificates tasks launched")
