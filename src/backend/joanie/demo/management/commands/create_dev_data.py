"""Management command to initialize simple data"""

from django.core.management.base import BaseCommand

from joanie.tests.testing_utils import Demo


class Command(BaseCommand):
    """Create simple data"""

    help = "Create simple data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--certificate",
            action="store_true",
            default=False,
            help="Create a certificate product.",
        )
        parser.add_argument(
            "--certificate-discount",
            action="store_true",
            default=False,
            help="Create a certificate product with a discount.",
        )
        parser.add_argument(
            "--credential",
            action="store_true",
            default=False,
            help="Create a credential product.",
        )
        parser.add_argument(
            "--credential-discount",
            action="store_true",
            default=False,
            help="Create a credential product with a discount.",
        )
        parser.add_argument(
            "--create-bunch-of-batch-orders",
            action="store_true",
            default=False,
            help="Create a bunch of batch orders.",
        )

    def handle(self, *args, **options):
        def log(message):
            """Log message"""
            self.stdout.write(self.style.SUCCESS(message))

        Demo(log=log).generate_simple(
            create_certificate=options.get("certificate"),
            create_certificate_discount=options.get("certificate_discount"),
            create_credential=options.get("credential"),
            create_credential_discount=options.get("credential_discount"),
            create_bunch_of_batch_orders=options.get("create_bunch_of_batch_orders"),
        )
