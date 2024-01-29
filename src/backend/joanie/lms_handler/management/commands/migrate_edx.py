"""Import data from OpenEdx database to Joanie database"""
import logging

from django.core.management import BaseCommand

from joanie.lms_handler.edx_imports.edx_import import (
    import_course_runs,
    import_enrollments,
    import_universities,
    import_users,
)

logging.StreamHandler.terminator = ""
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Import data from OpenEdx database to Joanie database"""

    def add_arguments(self, parser):
        """Add arguments to the command"""
        parser.add_argument(
            "--universities", action="store_true", help="Import universities"
        )
        parser.add_argument(
            "--course-runs", action="store_true", help="Import course runs"
        )
        parser.add_argument("--users", action="store_true", help="Import users")
        parser.add_argument(
            "--enrollments", action="store_true", help="Import enrollments"
        )
        parser.add_argument("--all", action="store_true", help="Import all")

    def handle(self, *args, **options):
        """Handle the command"""
        import_all = options["all"]
        universities_import = options["universities"] or import_all
        course_runs_import = options["course_runs"] or import_all
        users_import = options["users"] or import_all
        enrollments_import = options["enrollments"] or import_all

        if not any(
            [universities_import, course_runs_import, users_import, enrollments_import]
        ):
            self.stdout.write(self.style.ERROR("Nothing to import"))
            return

        if universities_import:
            import_universities()

        if course_runs_import:
            import_course_runs()

        if users_import:
            import_users()

        if enrollments_import:
            import_enrollments()
