"""Create_demo management command."""
import logging
import random
import time
from collections import defaultdict

from django import db
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

from joanie.core import enums, factories, models
from joanie.payment import models as payment_models

from ... import defaults

logger = logging.getLogger("joanie.commands.demo.create_demo")


def random_true_with_probability(probability):
    """return True with the requested probability, False otherwise."""
    return random.random() < probability  # nosec


class BulkQueue:
    """A utility class to create Django model instances in bulk by just pushing to a queue."""

    BATCH_SIZE = 20000

    def __init__(self, stdout, *args, **kwargs):
        """Define the queue as a dict of lists."""
        self.queue = defaultdict(list)
        self.stdout = stdout

    def _bulk_create(self, objects):
        """Actually create instances in bulk in the database."""
        if not objects:
            return

        objects[0]._meta.model.objects.bulk_create(objects, ignore_conflicts=True)
        # In debug mode, Django keeps query cache which creates a memory leak in this case
        db.reset_queries()
        self.queue[objects[0]._meta.model.__name__] = []

    def push(self, obj):
        """Add a model instance to queue to that it gets created in bulk."""
        objects = self.queue[obj._meta.model.__name__]
        objects.append(obj)
        if len(objects) > self.BATCH_SIZE:
            self._bulk_create(objects)
            self.stdout.write(".", ending="")

    def flush(self):
        """Flush the queue after creating the remaining model instances."""
        for objects in self.queue.values():
            self._bulk_create(objects)


class Timeit:
    """A utility context manager/method decorator to time execution."""

    total_time = 0

    def __init__(self, stdout, sentence=None):
        """Set the sentence to be displayed for timing information."""
        self.sentence = sentence
        self.start = None
        self.stdout = stdout

    def __call__(self, func):
        """Behavior on call for use as a method decorator."""

        def timeit_wrapper(*args, **kwargs):
            """wrapper to trigger/stop the timer before/after function call."""
            self.__enter__()
            result = func(*args, **kwargs)
            self.__exit__(None, None, None)
            return result

        return timeit_wrapper

    def __enter__(self):
        """Start timer upon entering context manager."""
        self.start = time.perf_counter()
        if self.sentence:
            self.stdout.write(self.sentence, ending=".")

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Stop timer and display result upon leaving context manager."""
        if exc_type is not None:
            raise exc_type(exc_value)
        end = time.perf_counter()
        elapsed_time = end - self.start
        if self.sentence:
            self.stdout.write(f" Took {elapsed_time:g} seconds")

        self.__class__.total_time += elapsed_time
        return elapsed_time


def create_free_enrollments(queue):
    """
    Create random enrollments in bulk.
    The number of enrollments actually created may vary due to conflicts that we decide
    to not handle because we only care about the order of magnitude of objects created.
    """
    state_choices = [s[0] for s in enums.ENROLLMENT_STATE_CHOICES]
    course_runs_ids = models.CourseRun.objects.values_list("id", flat=True)
    users_ids = models.User.objects.values_list("id", flat=True)
    nb_enrollments = (
        defaults.NB_OBJECTS["enrollments"] - models.Enrollment.objects.count()
    )
    for _i in range(nb_enrollments):
        queue.push(
            models.Enrollment(
                user_id=random.choice(users_ids),  # nosec
                course_run_id=random.choice(course_runs_ids),  # nosec
                is_active=random_true_with_probability(0.7),
                state=random.choice(state_choices),  # nosec
                was_created_by_order=False,
            )
        )
    queue.flush()


# pylint: disable=too-many-branches,too-many-locals,too-many-statements
def create_demo(stdout):
    """
    Create a database with demo data for developers to work in a realistic environment.
    """
    site = Site.objects.get(id=1)
    site.domain = getattr(settings, "JOANIE_DEMO_DOMAIN", defaults.DEFAULT_DEMO_DOMAIN)
    site.name = "Joanie demonstration"
    site.save()

    queue = BulkQueue(stdout)

    with Timeit(stdout, "Creating users"):
        for i in range(defaults.NB_OBJECTS["users"]):
            queue.push(
                models.User(
                    username=f"user{i:d}",
                    email=f"user{i:d}@example.com",
                    password="!",  # nosec
                    is_superuser=False,
                    is_active=True,
                    is_staff=False,
                    language="fr-fr",
                    first_name=f"Firstname {i:d}",
                    last_name=f"Lastname {i:d}",
                )
            )
        queue.flush()

    with Timeit(stdout, "Creating organizations"):
        factories.OrganizationFactory.create_batch(defaults.NB_OBJECTS["organizations"])

    with Timeit(stdout, "Creating courses"):
        factories.CourseFactory.create_batch(
            defaults.NB_OBJECTS["courses"] + defaults.NB_OBJECTS["products"]
        )

    with Timeit(stdout, "Creating certificate definitions"):
        factories.CertificateDefinitionFactory.create_batch(
            defaults.NB_OBJECTS["products"]
        )

    with Timeit(stdout, "Creating products"):
        for certificate_definition in models.CertificateDefinition.objects.only(
            "id"
        ).iterator():
            factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL,
                certificate_definition=certificate_definition,
                courses=[],
            )

    with Timeit(stdout, "Creating course runs"):
        # Create course runs only for courses not related to products
        for course in models.Course.objects.only("id").order_by("?")[
            : defaults.NB_OBJECTS["courses"]
        ]:
            factories.CourseRunFactory.create_batch(
                random.randint(1, 5), course=course  # nosec
            )

    with Timeit(stdout, "Creating product target course relations"):
        ids_of_courses_with_runs = list(
            models.Course.objects.filter(course_runs__isnull=False)
            .distinct()
            .values_list("id", flat=True)
        )
        for product_id in models.Product.objects.values_list("id", flat=True):
            for target_course_id in random.sample(
                ids_of_courses_with_runs,
                random.randint(2, min(30, len(ids_of_courses_with_runs))),  # nosec
            ):
                queue.push(
                    models.ProductTargetCourseRelation(
                        course_id=target_course_id,
                        product_id=product_id,
                        is_graded=random_true_with_probability(0.8),
                    )
                )
        queue.flush()
        del ids_of_courses_with_runs

    with Timeit(stdout, "Creating course product relations"):
        course_ids = models.Course.objects.filter(course_runs__isnull=True).values_list(
            "id", flat=True
        )
        product_ids = models.Product.objects.order_by("?").values_list("id", flat=True)

        for course_id, product_id in zip(course_ids, product_ids):
            queue.push(
                models.CourseProductRelation(course_id=course_id, product_id=product_id)
            )
        queue.flush()
        del course_ids
        del product_ids

    with Timeit(stdout, "Creating organization course product relations"):
        organization_ids = list(
            models.Organization.objects.values_list("id", flat=True)
        )
        for course_product_relation in models.CourseProductRelation.objects.iterator():
            course_product_relation.organizations.set(
                random.sample(organization_ids, random.randint(1, 3))  # nosec
            )
        del organization_ids

    with Timeit(stdout, "Creating orders"):
        users_ids = list(models.User.objects.values_list("id", flat=True))
        for product in models.Product.objects.iterator():
            course_dict = {}
            for relation in product.course_relations.all():
                course_dict[relation.course_id] = relation.organizations.values_list(
                    "id", flat=True
                )

            min_orders = max(1, defaults.NB_OBJECTS["max_orders_per_product"] // 10)
            for user_id in random.sample(
                users_ids,
                random.randint(  # nosec
                    min_orders, defaults.NB_OBJECTS["max_orders_per_product"]
                ),
            ):
                course_id = random.choice(list(course_dict.keys()))  # nosec
                queue.push(
                    models.Order(
                        organization_id=random.choice(course_dict[course_id]),  # nosec
                        course_id=course_id,
                        product_id=product.id,
                        owner_id=user_id,
                    )
                )
        queue.flush()
        del users_ids

    with Timeit(stdout, "Creating order target courses and related enrollments"):
        state_choices = [s[0] for s in enums.ENROLLMENT_STATE_CHOICES]
        course_runs_dict = {}
        for course in models.Course.objects.iterator():
            course_runs_dict[course.id] = course.course_runs.values_list(
                "id", flat=True
            )

        for product in models.Product.objects.iterator():
            target_course_relations = product.target_course_relations.all()
            for order in models.Order.objects.filter(product=product).iterator():
                for relation in target_course_relations:
                    queue.push(
                        models.OrderTargetCourseRelation(
                            course_id=relation.course_id,
                            order=order,
                            is_graded=relation.is_graded,
                            position=relation.position,
                        )
                    )
                    queue.push(
                        models.Enrollment(
                            user_id=order.owner_id,
                            course_run_id=random.choice(  # nosec
                                course_runs_dict[relation.course_id]
                            ),
                            is_active=random_true_with_probability(0.7),
                            state=random.choice(state_choices),  # nosec
                            was_created_by_order=True,
                        )
                    )
        queue.flush()
        del course_runs_dict

    with Timeit(stdout, "Creating enrollments not related to orders"):
        create_free_enrollments(queue)

    with Timeit(stdout, "Creating addresses and credit cards"):
        for user_sequence, user_id in enumerate(
            models.User.objects.filter(enrollments__was_created_by_order=True)
            .distinct()
            .values_list("id", flat=True)
        ):
            for i in range(random.randint(1, 3)):  # nosec
                queue.push(
                    models.Address(
                        title=f"Title {user_sequence:d}-{i:d}",
                        address=f"Address {user_sequence:d}-{i:d}",
                        postcode=f"Postcode {user_sequence:d}-{i:d}",
                        city=f"City {user_sequence:d}-{i:d}",
                        country=random.choice(["fr", "de"]),  # nosec
                        first_name=f"Fistname {user_sequence:d}-{i:d}",
                        last_name=f"Lastname {user_sequence:d}-{i:d}",
                        owner_id=user_id,
                    )
                )
            for i in range(random.randint(1, 3)):  # nosec
                queue.push(
                    payment_models.CreditCard(
                        title=f"Title {user_sequence:d}-{i:d}",
                        token=f"Token {user_sequence:d}-{i:d}",
                        brand=f"Brand {i:d}",
                        expiration_month=f"{random.randint(1, 12):02d}",  # nosec
                        expiration_year="2024",
                        last_numbers="1234",
                        owner_id=user_id,
                    )
                )
        queue.flush()


class Command(BaseCommand):
    """A management command to create a demo database."""

    help = __doc__

    def add_arguments(self, parser):
        """Add argument to required forcing execution when not in debug mode."""
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force command execution despite DEBUG is set to False",
        )

    def handle(self, *args, **options):
        """Handling of the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                (
                    "This command is not meant to be used in production environment "
                    "except you know what you are doing, if so use --force parameter"
                )
            )

        create_demo(self.stdout)
