# ruff: noqa: S311, PLR0913, PLR0915
"""Management command to initialize some fake data (products, courses and course runs)"""

from django.core.management.base import BaseCommand

from joanie.core.factories import fake_now
from joanie.tests.testing_utils import Demo


class Command(BaseCommand):
    """Create some fake data (products, courses and course runs)"""

    help = "Create some fake credential products, courses and course runs"

    def handle(self, *args, **options):
        def log(message):
            """Log message"""
            self.stdout.write(self.style.SUCCESS(message))

        with fake_now():
            Demo(log=log).generate()
