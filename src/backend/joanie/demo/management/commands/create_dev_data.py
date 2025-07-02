# ruff: noqa: S311, PLR0913, PLR0915
"""Management command to initialize simple data"""

from django.core.management.base import BaseCommand

from joanie.tests.testing_utils import Demo


class Command(BaseCommand):
    """Create simple data"""

    help = "Create simple data"

    def handle(self, *args, **options):
        def log(message):
            """Log message"""
            self.stdout.write(self.style.SUCCESS(message))

        Demo(log=log).generate_simple()
