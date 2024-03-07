"""Import data from Open edX database to Joanie database"""

import logging

from django.core.management import BaseCommand

from joanie.edx_imports.checks import (
    check_course_sync_env,
    check_import_db_connections,
    check_import_env,
    check_openedx_host,
)
from joanie.edx_imports.tasks.certificates import import_certificates
from joanie.edx_imports.tasks.course_runs import import_course_runs
from joanie.edx_imports.tasks.enrollments import import_enrollments
from joanie.edx_imports.tasks.universities import import_universities
from joanie.edx_imports.tasks.users import import_users

# pylint: disable=too-many-locals

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Import data from Open edX database to Joanie database"""

    def add_arguments(self, parser):
        """Add arguments to the command"""
        parser.add_argument(
            "--skip-check",
            action="store_true",
            default=False,
            help="Skip check the env vars and db connections",
        )
        parser.add_argument(
            "--universities", action="store_true", help="Import universities"
        )
        parser.add_argument(
            "--universities-offset",
            type=int,
            help="Offset to start importing universities",
            default=0,
        )
        parser.add_argument(
            "--universities-size",
            type=int,
            help="Size of universities to import",
            default=0,
        )
        parser.add_argument(
            "--course-runs", action="store_true", help="Import course runs"
        )
        parser.add_argument(
            "--course-runs-offset",
            type=int,
            help="Offset to start importing course runs",
            default=0,
        )
        parser.add_argument(
            "--course-runs-size",
            type=int,
            help="Size of course runs to import",
            default=0,
        )
        parser.add_argument("--users", action="store_true", help="Import users")
        parser.add_argument(
            "--users-offset",
            type=int,
            help="Offset to start importing users",
            default=0,
        )
        parser.add_argument(
            "--users-size", type=int, help="Size of users to import", default=0
        )
        parser.add_argument(
            "--enrollments", action="store_true", help="Import enrollments"
        )
        parser.add_argument(
            "--enrollments-offset",
            type=int,
            help="Offset to start importing enrollments",
            default=0,
        )
        parser.add_argument(
            "--enrollments-size",
            type=int,
            help="Size of enrollments to import",
            default=0,
        )
        parser.add_argument(
            "--certificates", action="store_true", help="Import certificates"
        )
        parser.add_argument(
            "--certificates-offset",
            type=int,
            help="Offset to start importing certificates",
            default=0,
        )
        parser.add_argument(
            "--certificates-limit",
            type=int,
            help="Limit of certificates to import",
            default=0,
        )
        parser.add_argument(
            "--course-id",
            type=str,
            help="Course id to import enrollments and certificates",
        )
        parser.add_argument("--all", action="store_true", help="Import all")
        parser.add_argument(
            "--batch-size",
            type=int,
            help="Batch size for importing users",
            default=1000,
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="Do not import anything",
            default=False,
        )

    def handle(self, *args, **options):
        """Handle the command"""
        skip_check = options["skip_check"]
        import_all = options["all"]
        universities_import = options["universities"] or import_all
        universities_import_offset = options["universities_offset"]
        universities_import_size = options["universities_size"]
        course_runs_import = options["course_runs"] or import_all
        course_runs_import_offset = options["course_runs_offset"]
        course_runs_import_size = options["course_runs_size"]
        users_import = options["users"] or import_all
        users_import_offset = options["users_offset"]
        users_import_size = options["users_size"]
        enrollments_import = options["enrollments"] or import_all
        enrollments_import_offset = options["enrollments_offset"]
        enrollments_import_size = options["enrollments_size"]
        certificates_import = options["certificates"] or import_all
        certificates_import_offset = options["certificates_offset"]
        certificates_import_limit = options["certificates_limit"]
        course_id = options["course_id"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if not skip_check:
            logger.info("Checking the environment and database connections...")
            check_result = check_import_env(self.style)
            check_result = check_course_sync_env(self.style) and check_result
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

        if not any(
            [
                universities_import,
                course_runs_import,
                users_import,
                enrollments_import,
                certificates_import,
            ]
        ):
            logger.error(self.style.ERROR("Nothing to import"))
            return

        logger.info("Importing data from Open edX database...")
        if universities_import:
            logger.info("Importing universities...")
            import_universities(
                global_offset=universities_import_offset,
                import_size=universities_import_size,
                dry_run=dry_run,
            )

        if course_runs_import:
            logger.info("Importing course runs...")
            import_course_runs(
                batch_size=batch_size,
                global_offset=course_runs_import_offset,
                import_size=course_runs_import_size,
                dry_run=dry_run,
            )

        if users_import:
            logger.info("Importing users...")
            import_users(
                batch_size=batch_size,
                global_offset=users_import_offset,
                import_size=users_import_size,
                dry_run=dry_run,
            )

        if enrollments_import:
            logger.info("Importing enrollments...")
            import_enrollments(
                batch_size=batch_size,
                global_offset=enrollments_import_offset,
                import_size=enrollments_import_size,
                course_id=course_id,
                dry_run=dry_run,
            )

        if certificates_import:
            logger.info("Importing certificates...")
            import_certificates(
                batch_size=batch_size,
                offset=certificates_import_offset,
                limit=certificates_import_limit,
                course_id=course_id,
                dry_run=dry_run,
            )
