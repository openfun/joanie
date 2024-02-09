"""Import data from Open edX database to Joanie database"""
import logging

from django.core.management import BaseCommand

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
            "--universities", action="store_true", help="Import universities"
        )
        parser.add_argument(
            "--universities-offset",
            type=int,
            help="Offset to start importing universities",
            default=0,
        )
        parser.add_argument(
            "--universities-limit",
            type=int,
            help="Limit of universities to import",
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
            "--course-runs-limit",
            type=int,
            help="Limit of course runs to import",
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
            "--users-limit", type=int, help="Limit of users to import", default=0
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
            "--enrollments-limit",
            type=int,
            help="Limit of enrollments to import",
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
        import_all = options["all"]
        universities_import = options["universities"] or import_all
        universities_import_offset = options["universities_offset"]
        universities_import_limit = options["universities_limit"]
        course_runs_import = options["course_runs"] or import_all
        course_runs_import_offset = options["course_runs_offset"]
        course_runs_import_limit = options["course_runs_limit"]
        users_import = options["users"] or import_all
        users_import_offset = options["users_offset"]
        users_import_limit = options["users_limit"]
        enrollments_import = options["enrollments"] or import_all
        enrollments_import_offset = options["enrollments_offset"]
        enrollments_import_limit = options["enrollments_limit"]
        certificates_import = options["certificates"] or import_all
        certificates_import_offset = options["certificates_offset"]
        certificates_import_limit = options["certificates_limit"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

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
                offset=universities_import_offset,
                limit=universities_import_limit,
                dry_run=dry_run,
            )

        if course_runs_import:
            logger.info("Importing course runs...")
            import_course_runs(
                offset=course_runs_import_offset,
                limit=course_runs_import_limit,
                dry_run=dry_run,
            )

        if users_import:
            logger.info("Importing users...")
            import_users(
                batch_size=batch_size,
                offset=users_import_offset,
                limit=users_import_limit,
                dry_run=dry_run,
            )

        if enrollments_import:
            logger.info("Importing enrollments...")
            import_enrollments(
                batch_size=batch_size,
                offset=enrollments_import_offset,
                limit=enrollments_import_limit,
                dry_run=dry_run,
            )

        if certificates_import:
            logger.info("Importing certificates...")
            import_certificates(
                batch_size=batch_size,
                offset=certificates_import_offset,
                limit=certificates_import_limit,
                dry_run=dry_run,
            )
