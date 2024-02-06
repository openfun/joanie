"""Import data from Open edX database to Joanie database"""
import logging

from django.core.management import BaseCommand

from joanie.edx_imports.tasks.universities import import_universities

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
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if not any(
            [universities_import]
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
