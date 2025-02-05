# pylint: disable=too-many-lines
# ruff: noqa: S311
"""
Core application factories
"""

import hashlib
import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.sites.models import Site
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

import factory.fuzzy
from easy_thumbnails.files import ThumbnailerImageFieldFile, generate_all_aliases
from faker import Faker
from timedelta_isoformat import timedelta as timedelta_isoformat

from joanie.core import enums, models
from joanie.core.models import (
    CourseState,
    DocumentImage,
    OrderTargetCourseRelation,
    ProductTargetCourseRelation,
)
from joanie.core.serializers import AddressSerializer
from joanie.core.utils import contract_definition, file_checksum, payment_schedule
from joanie.core.utils.payment_schedule import (
    convert_amount_str_to_money_object,
    convert_date_str_to_date_object,
)

logger = logging.getLogger(__name__)


def generate_thumbnails_for_field(field, include_global=False):
    """
    Generate thumbnails for a given field.
    """
    if isinstance(field, ThumbnailerImageFieldFile) and field:
        field.get_thumbnail({"size": (field.width, field.height)})
        generate_all_aliases(field, include_global=include_global)


class UniqueFaker(factory.Faker):
    """A Faker util that ensures values uniqueness."""

    @classmethod
    def _get_faker(cls, locale=None):
        """Get a faker that ensures values uniqueness."""
        return super()._get_faker(locale=locale).unique


class DebugModelFactory:
    """
    A factory to create Django models with logging of the created instances.
    """

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Create an instance of the model, log it and return it.
        """
        instance = super()._create(model_class, *args, **kwargs)  # pylint: disable=no-member
        logger.debug(
            "Created %s instance: %s class: %s",
            model_class.__name__,
            instance,
            cls.__name__,
        )
        # logger.debug(" with args %s, kwargs %s", args, kwargs)
        return instance


class UserFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """
    A factory to create an authenticated user for joanie side
    (to manage objects on admin interface)
    """

    class Meta:
        model = settings.AUTH_USER_MODEL
        django_get_or_create = ("username",)

    # In our database, first_name is set by authtoken with the user's full name
    first_name = factory.Faker("name")
    username = factory.Sequence(lambda n: f"user{n!s}")
    email = factory.Faker("email")
    language = factory.fuzzy.FuzzyChoice([lang[0] for lang in settings.LANGUAGES])
    password = make_password("password")


class CertificateDefinitionFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """A factory to create a certificate definition"""

    class Meta:
        model = models.CertificateDefinition
        django_get_or_create = ("name",)

    title = factory.Sequence(lambda n: f"Certificate definition {n}")
    name = factory.Sequence(lambda n: f"certificate-definition-{n}")
    template = factory.fuzzy.FuzzyChoice(
        [name[0] for name in enums.CERTIFICATE_NAME_CHOICES]
    )


class ContractDefinitionFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a contract definition"""

    class Meta:
        model = models.ContractDefinition

    body = factory.Faker("paragraphs", nb=3)
    description = factory.Faker("paragraph", nb_sentences=5)
    language = factory.fuzzy.FuzzyChoice([lang[0] for lang in settings.LANGUAGES])
    name = factory.fuzzy.FuzzyChoice([name[0] for name in enums.CONTRACT_NAME_CHOICES])
    title = factory.Sequence(lambda n: f"Contract definition {n}")


class OrganizationFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create an organization"""

    class Meta:
        model = models.Organization
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: n)
    title = factory.Sequence(lambda n: f"Organization {n}")
    representative = factory.Faker("name")
    signature = factory.django.ImageField(
        filename="signature.png", format="png", width=1, height=1
    )
    logo = factory.django.ImageField(
        filename="logo.png", format="png", width=1, height=1
    )

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        """Add users to organization from a given list of users with or without roles."""
        if create and extracted:
            for item in extracted:
                if isinstance(item, models.User):
                    UserOrganizationAccessFactory(organization=self, user=item)
                else:
                    UserOrganizationAccessFactory(
                        organization=self, user=item[0], role=item[1]
                    )


class OrganizationFactoryWithThumbnails(OrganizationFactory):
    """A factory to create an organization, with thumbnails generation"""

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """
        Generate thumbnails for logo after organization has been created.
        """
        if create:
            generate_thumbnails_for_field(instance.logo)


class UserOrganizationAccessFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """Create fake organization user accesses for testing."""

    class Meta:
        model = models.OrganizationAccess

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.fuzzy.FuzzyChoice(
        [r[0] for r in models.OrganizationAccess.ROLE_CHOICES]
    )


class CourseFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a course"""

    class Meta:
        model = models.Course
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda k: f"{k:05d}")
    title = factory.Sequence(lambda n: f"Course {n}")
    cover = factory.django.ImageField(
        filename="cover.png", format="png", width=1, height=1
    )
    effort = factory.Faker("time_delta", end_datetime=timedelta(hours=100))

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def organizations(self, create, extracted, **kwargs):
        """
        Link organizations to the course after its creation:
        - link the list of organizations passed in "extracted" if any
        """
        if not extracted:
            return

        self.organizations.set(extracted)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def products(self, create, extracted, **kwargs):
        """
        Link products to the course after its creation:
        - link the list of products passed in "extracted" if any
        """
        if extracted is None:
            return

        for product in extracted:
            CourseProductRelationFactory(course=self, product=product)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def course_runs(self, create, extracted, **kwargs):
        """
        Link course_runs to the course after its creation:
        - link the list of course_runs passed in "extracted" if any
        """
        if not extracted:
            return

        self.course_runs.set(extracted)

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        """Add users to course from a given list of users with or without roles."""
        if create and extracted:
            for item in extracted:
                if isinstance(item, models.User):
                    UserCourseAccessFactory(course=self, user=item)
                else:
                    UserCourseAccessFactory(course=self, user=item[0], role=item[1])


class CourseFactoryWithThumbnails(CourseFactory):
    """A factory to create a course, with thumbnails generation"""

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """
        Generate thumbnails for cover after course has been created.
        """
        if create:
            generate_thumbnails_for_field(instance.cover)


class UserCourseAccessFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """Create fake course user accesses for testing."""

    class Meta:
        model = models.CourseAccess

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.fuzzy.FuzzyChoice([r[0] for r in models.CourseAccess.ROLE_CHOICES])


class CourseRunFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """
    A factory to easily generate a credible openEdx course run for our tests.
    """

    class Params:
        """Parameters for the factory."""

        state = None
        ref_date = factory.LazyAttribute(lambda o: django_timezone.now())

    class Meta:
        model = models.CourseRun
        django_get_or_create = ("resource_link",)

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Course run {n}")

    # pylint: disable=no-self-use
    @factory.lazy_attribute
    def languages(self):
        """
        Compute a random set of languages from the complete list of Django supported languages.
        """
        return {random.choice(enums.ALL_LANGUAGES)[0]}

    @factory.lazy_attribute_sequence
    def resource_link(self, sequence):
        """Generate a resource link that looks like an OpenEdX course url."""
        code = self.course.code if self.course else "0001"
        return (
            f"http://openedx.test/courses/course-v1:edx+{code!s}+{sequence:d}/course/"
        )

    @factory.lazy_attribute
    def start(self):
        """
        Compute a start date according to the course run state and the ref date. Otherwise,
        a start datetime for the course run is chosen randomly in the past/future
        in the range of 1 to 365 days (it can of course be forced if we want something else),
        then the other significant dates for the course run are chosen randomly in periods
        that make sense with this start date.
        """
        if self.state == models.CourseState.TO_BE_SCHEDULED:
            return None

        period = timedelta(days=random.randrange(1, 365, 1))  # between 1 and 365 days

        if self.state in [
            models.CourseState.ONGOING_OPEN,
            models.CourseState.ONGOING_CLOSED,
            models.CourseState.ARCHIVED_OPEN,
            models.CourseState.ARCHIVED_CLOSED,
        ]:
            # The course run is on going or archived,
            # so the start date must be less than the ref date
            min_date = self.ref_date - period
            max_date = self.ref_date
        elif self.state in [
            models.CourseState.FUTURE_OPEN,
            models.CourseState.FUTURE_NOT_YET_OPEN,
            models.CourseState.FUTURE_CLOSED,
        ]:
            # The course run has not yet started,
            # so the start date must be greater than the ref date
            min_date = self.ref_date
            max_date = self.ref_date + period
        else:
            # Otherwise, the start date can be chosen randomly in the past/future
            min_date = self.ref_date - period
            max_date = self.ref_date + period

        return datetime.utcfromtimestamp(
            random.randrange(int(min_date.timestamp()), int(max_date.timestamp()))
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def end(self):
        """
        Compute the end date according to the course run state and the ref date.
        Otherwise, pick a random date in the range of 1 to 365 days after the start date
        """
        if not self.start:
            return None

        period = timedelta(days=random.randrange(1, 365, 1))  # between 1 and 365 days

        if self.state in [
            models.CourseState.ARCHIVED_OPEN,
            models.CourseState.ARCHIVED_CLOSED,
        ]:
            # The course run is archived, end date must be less than ref date
            if self.start >= self.ref_date:
                raise ValueError("Start date must be less than ref date.")
            min_date = self.start
            max_date = self.ref_date
        elif self.state in [
            models.CourseState.ONGOING_OPEN,
            models.CourseState.ONGOING_CLOSED,
        ]:
            # The course run is on going, end date must be greater than ref_date
            min_date = self.ref_date
            max_date = min_date + period
        elif self.state in [
            models.CourseState.FUTURE_NOT_YET_OPEN,
            models.CourseState.FUTURE_OPEN,
            models.CourseState.FUTURE_CLOSED,
        ]:
            min_date = max(self.ref_date, self.start)
            max_date = min_date + period
        else:
            # Otherwise, we just want end date to be greater than start date
            min_date = self.start
            max_date = min_date + period

        return datetime.utcfromtimestamp(
            random.randrange(int(min_date.timestamp()), int(max_date.timestamp()))
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def enrollment_start(self):
        """
        Compute the enrollment start date according to the course run state
        and the ref date. Otherwise, pick a random date in the range of 1 to 90 days
        before the start date.
        """
        if not self.start:
            return None

        period = timedelta(days=random.randrange(1, 90, 1))  # between 1 and 90 days

        if self.state in [
            models.CourseState.FUTURE_OPEN,
            models.CourseState.FUTURE_CLOSED,
        ]:
            # The course run enrollment has not yet started,
            # so the enrollment start date must be less than the ref date
            min_date = self.ref_date - period
            max_date = self.ref_date
        elif self.state == models.CourseState.FUTURE_NOT_YET_OPEN:
            # The course run is not yet open for enrollment,
            # so the enrollment start date must be greater than the ref date
            if self.start <= self.ref_date:
                raise ValueError("Start date must be greater than ref date.")
            min_date = self.ref_date
            max_date = self.start
        else:
            # Otherwise, the enrollment start date can be in the past or in the future
            min_date = self.start - period
            max_date = self.start

        return datetime.utcfromtimestamp(
            random.randrange(int(min_date.timestamp()), int(max_date.timestamp()))
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def enrollment_end(self):
        """
        Compute the enrollment end date according to the course run state
        and the ref date. Otherwise, pick a random date in the range of enrollment
        start date and end date.
        """
        if (
            not self.start
            or not self.enrollment_start
            or self.state == models.CourseState.ARCHIVED_OPEN
        ):
            # Archived open state is a special case.
            # The course run has ended but enrollment is still opened.
            return None

        period = timedelta(days=random.randrange(1, 90, 1))  # between 1 and 90 days

        if self.state in [
            models.CourseState.ONGOING_OPEN,
            models.CourseState.FUTURE_OPEN,
        ]:
            # The course run is opened for enrollment, so the enrollment end date must
            # be greater than the ref date and less than the course run end
            if self.end and self.end <= self.ref_date:
                raise ValueError("End date must be greater than ref date.")
            min_date = self.ref_date
            max_date = self.end or self.ref_date + period
        elif self.state in [
            models.CourseState.ONGOING_CLOSED,
            models.CourseState.FUTURE_CLOSED,
        ]:
            # The course run is closed for enrollment,
            # so the enrollment end date must be less than the ref date
            min_date = self.ref_date - period
            max_date = self.ref_date
        else:
            # Otherwise, the enrollment end must be in the range of
            # the enrollment start and the end of the course run.
            # About course run not yet opened for enrollment, the enrollment end date
            # must be greater than the enrollment start date too.
            # (as this one is greater than the ref date)
            if self.end and self.end <= self.enrollment_start:
                raise ValueError("End date must be greater than enrollment start date.")
            min_date = self.enrollment_start
            max_date = self.end or self.enrollment_start + period

        return datetime.utcfromtimestamp(
            random.randrange(int(min_date.timestamp()), int(max_date.timestamp()))
        ).replace(tzinfo=timezone.utc)


class CourseRunMoodleFactory(CourseRunFactory):
    """
    A factory to easily generate a credible Moodle course run for our tests.
    """

    @factory.lazy_attribute_sequence
    def resource_link(self, sequence):
        """Generate a resource link that looks like a Moodle course url."""
        return f"http://moodle.test/course/view.php?id={sequence:d}"


class EnrollmentFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create an enrollment"""

    class Meta:
        model = models.Enrollment
        django_get_or_create = (
            "course_run",
            "user",
        )

    # Create an enrollable course run for free by default
    course_run = factory.SubFactory(
        CourseRunFactory,
        is_listed=True,
        state=factory.fuzzy.FuzzyChoice(
            [
                models.CourseState.ONGOING_OPEN,
                models.CourseState.FUTURE_OPEN,
                models.CourseState.ARCHIVED_OPEN,
            ]
        ),
    )
    user = factory.SubFactory(UserFactory)
    is_active = factory.fuzzy.FuzzyChoice([True, False])
    state = factory.fuzzy.FuzzyChoice([s[0] for s in enums.ENROLLMENT_STATE_CHOICES])


class ProductFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a product"""

    class Meta:
        model = models.Product
        skip_postgeneration_save = True

    type = enums.PRODUCT_TYPE_CREDENTIAL
    title = factory.Faker("bs")
    call_to_action = "let's go!"
    price = Faker().pydecimal(left_digits=3, right_digits=2, min_value=0)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def courses(self, create, extracted, **kwargs):
        """
        Link courses to the product after its creation:
        - link the list of courses passed in "extracted" if any
        - otherwise create a random course and link it
        """
        if extracted is None:
            if create:
                CourseProductRelationFactory(product=self, course=CourseFactory())
            return

        for course in extracted:
            course__organizations = course.organizations.all()
            CourseProductRelationFactory(
                product=self,
                course=course,
                organizations=course__organizations
                if len(course__organizations)
                else None,
            )

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def target_courses(self, create, extracted, **kwargs):
        """
        Link target courses to the product after its creation:
        - link the list of courses passed in "extracted" if any
        """
        if not extracted or not create:
            return

        for position, course in enumerate(extracted):
            ProductTargetCourseRelationFactory(
                product=self, course=course, position=position
            )

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        """
        Link teachers to the product after its creation:
        - link the list of teachers passed in "extracted" if any
        """
        if not extracted or not create:
            return

        self.teachers.set(extracted)

    @factory.post_generation
    def skills(self, create, extracted, **kwargs):
        """
        Link skills to the product after its creation:
        - link the list of skills passed in "extracted" if any
        """
        if not extracted or not create:
            return

        self.skills.set(extracted)

    @factory.lazy_attribute
    def certificate_definition(self):
        """
        Return a CertificateDefinition object with a random name and a random
        description if the product type allows to have a certificate.
        """
        if self.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED:
            return None

        return CertificateDefinitionFactory()


class DiscountFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a discount"""

    class Meta:
        model = models.Discount

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create an instance of the model, and save it to the database."""
        if "rate" not in kwargs and "amount" not in kwargs:
            if random.choice([True, False]):
                kwargs["rate"] = Faker().pyfloat(
                    left_digits=1, right_digits=4, positive=True, max_value=1
                )
            else:
                kwargs["amount"] = Faker().pyint(min_value=0, max_value=100, step=5)
        return super()._create(model_class, *args, **kwargs)


class CourseProductRelationFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """A factory to create CourseProductRelation object"""

    class Meta:
        model = models.CourseProductRelation
        skip_postgeneration_save = True

    product = factory.SubFactory(ProductFactory)
    course = factory.SubFactory(CourseFactory)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def organizations(self, create, extracted, **kwargs):
        """
        Link organizations to the course/product relation after its creation
        """
        if extracted is None:
            extracted = [OrganizationFactory()]

        self.organizations.set(extracted)


class ProductTargetCourseRelationFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """A factory to create ProductTargetCourseRelation object"""

    class Meta:
        model = models.ProductTargetCourseRelation
        skip_postgeneration_save = True
        django_get_or_create = ("product", "course")

    product = factory.SubFactory(ProductFactory)
    course = factory.SubFactory(CourseFactory)
    position = factory.fuzzy.FuzzyInteger(0, 1000)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def course_runs(self, create, extracted, **kwargs):
        """
        Link course runs to the product/target course relation after its creation
        """
        if not extracted:
            return

        self.course_runs.set(extracted)


class OrderGroupFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create order groups."""

    class Meta:
        model = models.OrderGroup

    course_product_relation = factory.SubFactory(CourseProductRelationFactory)
    nb_seats = factory.fuzzy.FuzzyInteger(0, 100)


class OrderFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create an Order"""

    class Meta:
        model = models.Order

    product = factory.SubFactory(ProductFactory)
    course = factory.LazyAttribute(lambda o: o.product.courses.order_by("?").first())
    total = factory.LazyAttribute(lambda o: o.product.price)
    enrollment = None

    @factory.lazy_attribute
    def owner(self):
        """Retrieve the user from the enrollment when available or create a new one."""
        if self.enrollment:
            return self.enrollment.user
        return UserFactory()

    @factory.lazy_attribute
    def organization(self):
        """Retrieve the organization from the product/course relation."""
        course_relations = self.product.course_relations
        if self.course:
            course_relations = course_relations.filter(course=self.course)
        return course_relations.first().organizations.order_by("?").first()

    @factory.lazy_attribute
    def credit_card(self):
        """Create a credit card for the order."""
        if self.product.price == 0:
            return None
        from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
            CreditCardFactory,
        )

        return CreditCardFactory(owner=self.owner)

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def target_courses(self, create, extracted, **kwargs):
        """
        If the order has a state other than draft, it should have been submitted so
        target courses should have been copied from the product target courses.
        """
        if extracted:
            self.target_courses.set(extracted)

        if self.state != enums.ORDER_STATE_DRAFT:
            for relation in ProductTargetCourseRelation.objects.filter(
                product=self.product
            ):
                order_relation = OrderTargetCourseRelation.objects.create(
                    order=self,
                    course=relation.course,
                    position=relation.position,
                    is_graded=relation.is_graded,
                )
                order_relation.course_runs.set(relation.course_runs.all())

    @factory.post_generation
    def main_invoice(self, create, extracted, **kwargs):
        """
        Generate invoice if needed
        """
        if create:
            if extracted is not None:
                # If a main_invoice is passed, link it to the order.
                extracted.order = self
                extracted.save()
                return extracted

            if self.state != enums.ORDER_STATE_DRAFT and not self.is_free:
                from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
                    InvoiceFactory,
                    TransactionFactory,
                )

                if (
                    self.product.type in enums.PRODUCT_TYPE_CERTIFICATE
                    and self.state
                    in [
                        enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                        enums.ORDER_STATE_PENDING_PAYMENT,
                    ]
                ):
                    return InvoiceFactory(
                        order=self,
                        recipient_address__owner=self.owner,
                        total=self.total,
                    )

                # If the order is not free and its state is not 'draft'
                # and the product has a contract create a main invoice with related transaction.
                transaction = TransactionFactory(
                    invoice__order=self,
                    invoice__recipient_address__owner=self.owner,
                    total=self.total,
                )
                return transaction.invoice

        return None

    @factory.post_generation
    # pylint: disable=method-hidden
    def payment_schedule(self, create, extracted, **kwargs):
        """
        Cast input strings for the fields `amount` and `due_date` into the appropriate types
        """
        if create and extracted:
            for item in extracted:
                if isinstance(item["due_date"], str):
                    item["due_date"] = convert_date_str_to_date_object(item["due_date"])
                if isinstance(item["amount"], str):
                    item["amount"] = convert_amount_str_to_money_object(item["amount"])
            self.payment_schedule = extracted
            return extracted
        return None


class OrderGeneratorFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create an Order"""

    class Meta:
        model = models.Order

    product = factory.SubFactory(ProductFactory)
    course = factory.LazyAttribute(lambda o: o.product.courses.order_by("?").first())
    total = factory.LazyAttribute(lambda o: o.product.price)
    enrollment = None
    state = enums.ORDER_STATE_DRAFT

    @factory.lazy_attribute
    def owner(self):
        """Retrieve the user from the enrollment when available or create a new one."""
        if self.enrollment:
            return self.enrollment.user
        return UserFactory(language="en-us")

    @factory.lazy_attribute
    def organization(self):
        """Retrieve the organization from the product/course relation."""
        if self.state == enums.ORDER_STATE_DRAFT:
            return None

        course_relations = self.product.course_relations
        if self.course:
            course_relations = course_relations.filter(course=self.course)
        return course_relations.first().organizations.order_by("?").first()

    @factory.post_generation
    def main_invoice(self, create, extracted, **kwargs):
        """
        Generate invoice if needed
        """
        if create:
            if extracted is not None:
                # If a main_invoice is passed, link it to the order.
                extracted.order = self
                extracted.save()
                return extracted

            if self.state != enums.ORDER_STATE_DRAFT:
                from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
                    InvoiceFactory,
                )

                return InvoiceFactory(
                    order=self,
                    total=self.total,
                    recipient_address__owner=self.owner,
                )

        return None

    @factory.post_generation
    # pylint: disable=unused-argument
    def contract(self, create, extracted, **kwargs):
        """Create a contract for the order."""
        if extracted:
            return extracted

        if self.state in [
            enums.ORDER_STATE_TO_SIGN,
            enums.ORDER_STATE_SIGNING,
            enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_NO_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_COMPLETED,
            enums.ORDER_STATE_CANCELED,
            enums.ORDER_STATE_REFUNDING,
            enums.ORDER_STATE_REFUNDED,
        ]:
            if not self.product.contract_definition:
                self.product.contract_definition = ContractDefinitionFactory()
                self.product.save()

            is_signed = self.state not in [
                enums.ORDER_STATE_TO_SIGN,
                enums.ORDER_STATE_SIGNING,
            ]
            context = kwargs.get(
                "context",
                contract_definition.generate_document_context(
                    contract_definition=self.product.contract_definition,
                    user=self.owner,
                    order=self,
                )
                if is_signed
                else None,
            )
            student_signed_on = kwargs.get(
                "student_signed_on", django_timezone.now() if is_signed else None
            )
            organization_signed_on = kwargs.get(
                "organization_signed_on",
                django_timezone.now() if is_signed else None,
            )
            submitted_for_signature_on = kwargs.get(
                "submitted_for_signature_on",
                django_timezone.now()
                if student_signed_on and not organization_signed_on
                else None,
            )
            definition_checksum = kwargs.get(
                "definition_checksum",
                "fake_test_file_hash_1" if is_signed else None,
            )
            signature_backend_reference = kwargs.get(
                "signature_backend_reference",
                f"wfl_fake_dummy_demo_dev_{uuid.uuid4()}" if is_signed else None,
            )
            return ContractFactory(
                order=self,
                student_signed_on=student_signed_on,
                submitted_for_signature_on=submitted_for_signature_on,
                organization_signed_on=organization_signed_on,
                definition=self.product.contract_definition,
                context=context,
                definition_checksum=definition_checksum,
                signature_backend_reference=signature_backend_reference,
            )

        return None

    @factory.lazy_attribute
    def credit_card(self):
        """Create a credit card for the order."""
        if self.state in [
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_NO_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_COMPLETED,
            enums.ORDER_STATE_CANCELED,
            enums.ORDER_STATE_REFUNDING,
            enums.ORDER_STATE_REFUNDED,
        ]:
            from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
                CreditCardFactory,
            )

            return CreditCardFactory(owner=self.owner)

        return None

    @factory.post_generation
    # pylint: disable=unused-argument
    def target_courses(self, create, extracted, **kwargs):
        """
        If the order has a state other than draft, it should have been init so
        target courses should have been copied from the product target courses.
        """
        if not extracted or not create:
            return

        for position, course in enumerate(extracted):
            OrderTargetCourseRelationFactory(
                order=self,
                course=course,
                position=position,
            )

    @factory.post_generation
    # pylint: disable=unused-argument, too-many-branches, too-many-statements
    # ruff: noqa: PLR0912, PLR0915
    def billing_address(self, create, extracted, **kwargs):
        """
        Create a billing address for the order.
        This method also handles the state transitions of the order based on the target state
        and whether the order is free or not.
        It updates the payment schedule states accordingly.
        """
        target_state = self.state
        if self.state not in [
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_ASSIGNED,
        ]:
            self.state = enums.ORDER_STATE_DRAFT

            if not self.product.target_courses.exists():
                CourseRunFactory(
                    course=self.course,
                    is_gradable=True,
                    state=CourseState.ONGOING_OPEN,
                    end=django_timezone.now() + timedelta(days=200),
                )
                ProductTargetCourseRelationFactory(
                    product=self.product,
                    course=self.course,
                    is_graded=True,
                )

            if extracted:
                self.init_flow(billing_address=extracted)
            else:
                from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
                    BillingAddressDictFactory,
                )

                self.init_flow(billing_address=BillingAddressDictFactory())

        if target_state == enums.ORDER_STATE_SIGNING:
            if not self.contract.submitted_for_signature_on:
                self.submit_for_signature(self.owner)
            else:
                self.state = target_state
                self.save()

        if (
            not self.is_free
            and self.has_contract
            and target_state
            not in [
                enums.ORDER_STATE_DRAFT,
                enums.ORDER_STATE_ASSIGNED,
                enums.ORDER_STATE_TO_SIGN,
            ]
        ):
            self.generate_schedule()

        if (
            target_state
            in [
                enums.ORDER_STATE_PENDING_PAYMENT,
                enums.ORDER_STATE_NO_PAYMENT,
                enums.ORDER_STATE_FAILED_PAYMENT,
                enums.ORDER_STATE_COMPLETED,
                enums.ORDER_STATE_REFUNDING,
                enums.ORDER_STATE_REFUNDED,
            ]
            and not self.is_free
        ):
            from joanie.payment.factories import (  # pylint: disable=import-outside-toplevel, cyclic-import
                TransactionFactory,
            )

            if target_state in [
                enums.ORDER_STATE_PENDING_PAYMENT,
                enums.ORDER_STATE_REFUNDING,
                enums.ORDER_STATE_REFUNDED,
            ]:
                self.payment_schedule[0]["state"] = enums.PAYMENT_STATE_PAID
                # Create related transactions when an installment is paid
                TransactionFactory(
                    invoice__order=self,
                    invoice__parent=self.main_invoice,
                    invoice__total=0,
                    invoice__recipient_address__owner=self.owner,
                    total=str(self.payment_schedule[0]["amount"]),
                    reference=self.payment_schedule[0]["id"],
                )
            if target_state == enums.ORDER_STATE_NO_PAYMENT:
                self.payment_schedule[0]["state"] = enums.PAYMENT_STATE_REFUSED
            if target_state == enums.ORDER_STATE_FAILED_PAYMENT:
                self.state = target_state
                self.payment_schedule[0]["state"] = enums.PAYMENT_STATE_PAID
                self.payment_schedule[1]["state"] = enums.PAYMENT_STATE_REFUSED
                TransactionFactory(
                    invoice__order=self,
                    invoice__parent=self.main_invoice,
                    invoice__total=0,
                    invoice__recipient_address__owner=self.owner,
                    total=str(self.payment_schedule[0]["amount"]),
                    reference=self.payment_schedule[0]["id"],
                )
            if target_state == enums.ORDER_STATE_COMPLETED:
                self.flow.update()
                for payment in self.payment_schedule:
                    payment["state"] = enums.PAYMENT_STATE_PAID
                    TransactionFactory(
                        invoice__order=self,
                        invoice__parent=self.main_invoice,
                        invoice__total=0,
                        invoice__recipient_address__owner=self.owner,
                        total=str(payment["amount"]),
                        reference=payment["id"],
                    )

            self.save()
            self.flow.update()

        if target_state == enums.ORDER_STATE_CANCELED:
            self.flow.cancel()

        if (
            self.state == enums.ORDER_STATE_PENDING_PAYMENT
            and target_state == enums.ORDER_STATE_REFUNDING
            and payment_schedule.has_installment_paid(self)
        ):
            self.flow.cancel()
            self.flow.refunding()

        if (
            self.state == enums.ORDER_STATE_PENDING_PAYMENT
            and target_state == enums.ORDER_STATE_REFUNDED
        ):
            self.flow.cancel()
            self.flow.refunding()
            self.payment_schedule[0]["state"] = enums.PAYMENT_STATE_REFUNDED
            installment_id = self.payment_schedule[0]["id"]
            TransactionFactory(
                invoice__order=self,
                invoice__parent=self.main_invoice,
                invoice__total=0,
                invoice__recipient_address__owner=self.owner,
                total=-Decimal(str(self.payment_schedule[0]["amount"])),
                reference=f"ref_{installment_id}",
            )
            self.cancel_remaining_installments()
            self.save()
            self.flow.refunded()

    @factory.post_generation
    # pylint: disable=method-hidden
    def payment_schedule(self, create, extracted, **kwargs):
        """
        Cast input strings for the fields `amount` and `due_date` into the appropriate types
        """
        if create and extracted:
            for item in extracted:
                if isinstance(item["due_date"], str):
                    item["due_date"] = convert_date_str_to_date_object(item["due_date"])
                if isinstance(item["amount"], str):
                    item["amount"] = convert_amount_str_to_money_object(item["amount"])
            self.payment_schedule = extracted
            return extracted
        return None


class OrderTargetCourseRelationFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """A factory to create OrderTargetCourseRelation object"""

    class Meta:
        model = models.OrderTargetCourseRelation

    order = factory.SubFactory(OrderFactory)
    course = factory.SubFactory(CourseFactory)
    position = factory.fuzzy.FuzzyInteger(0, 1000)


class AddressFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create an address"""

    class Meta:
        model = models.Address

    title = factory.fuzzy.FuzzyChoice(["Home", "Office"])
    address = factory.Faker("street_address")
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class UserAddressFactory(AddressFactory):
    """A factory to create a user address"""

    owner = factory.SubFactory(UserFactory)


class OrganizationAddressFactory(AddressFactory):
    """A factory to create an organization address"""

    organization = factory.SubFactory(OrganizationFactory)


class OrderCertificateFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a certificate"""

    class Meta:
        model = models.Certificate

    order = factory.SubFactory(
        OrderFactory,
        product__type=enums.PRODUCT_TYPE_CREDENTIAL,
    )

    @factory.lazy_attribute
    def certificate_definition(self):
        """
        Return the order product certificate definition.
        """
        return self.order.product.certificate_definition

    @factory.lazy_attribute
    def organization(self):
        """Return the order organization."""
        return self.order.organization


class EnrollmentCertificateFactory(
    DebugModelFactory, factory.django.DjangoModelFactory
):
    """
    A factory to create a certificate directly related to an enrollment (not through an order)
    """

    class Meta:
        model = models.Certificate

    enrollment = factory.SubFactory(EnrollmentFactory)
    certificate_definition = factory.SubFactory(CertificateDefinitionFactory)
    organization = factory.SubFactory(OrganizationFactory)


class CourseWishFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a course wish for a user."""

    class Meta:
        model = models.CourseWish

    course = factory.SubFactory(CourseFactory)
    owner = factory.SubFactory(UserFactory)


class ContractFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """A factory to create a contract"""

    class Meta:
        model = models.Contract

    order = factory.SubFactory(
        OrderFactory,
        state=enums.ORDER_STATE_COMPLETED,
        product__type=enums.PRODUCT_TYPE_CREDENTIAL,
        product__contract_definition=factory.SubFactory(ContractDefinitionFactory),
    )
    student_signed_on = None
    organization_signed_on = None
    submitted_for_signature_on = None

    @factory.lazy_attribute
    def definition(self):
        """
        Return the order product contract definition.
        """
        return self.order.product.contract_definition

    @factory.lazy_attribute
    def context(self):
        """
        Lazily generate the contract context from the related order and contract definition.
        """
        if self.student_signed_on or self.submitted_for_signature_on:
            student_address = self.order.owner.addresses.filter(is_main=True).first()
            organization_address = self.order.organization.addresses.filter(
                is_main=True
            ).first()
            course_dates = self.order.get_equivalent_course_run_dates()

            logo_checksum = file_checksum(self.order.organization.logo)
            logo_image, created = DocumentImage.objects.get_or_create(
                checksum=logo_checksum,
                defaults={"file": self.order.organization.logo},
            )
            if created:
                self.definition.images.set([logo_image])
            organization_logo_id = str(logo_image.id)

            return {
                "contract": {
                    "body": self.definition.get_body_in_html(),
                    "appendix": self.definition.get_appendix_in_html(),
                    "title": self.definition.title,
                },
                "course": {
                    "name": self.order.product.safe_translation_getter(
                        "title", language_code=self.definition.language
                    ),
                    "code": self.order.course.code,
                    "start": (
                        course_dates["start"].isoformat()
                        if course_dates["start"] is not None
                        else _("<COURSE_START_DATE>")
                    ),
                    "end": (
                        course_dates["end"].isoformat()
                        if course_dates["end"] is not None
                        else _("<COURSE_END_DATE>")
                    ),
                    "effort": (
                        timedelta_isoformat(
                            seconds=self.order.course.effort.total_seconds()
                        ).isoformat()
                        if self.order
                        else _("<EFFORT_DURATION>")
                    ),
                    "price": str(self.order.total),
                },
                "student": {
                    "name": self.order.owner.get_full_name()
                    or self.order.owner.username,
                    "address": AddressSerializer(student_address).data,
                    "email": self.order.owner.email,
                    "phone_number": self.order.owner.phone_number,
                    "payment_schedule": [
                        {
                            "due_date": installment["due_date"].isoformat(),
                            "amount": str(installment["amount"]),
                        }
                        for installment in self.order.payment_schedule
                    ]
                    if self.order.payment_schedule
                    else None,
                },
                "organization": {
                    "logo_id": organization_logo_id,
                    "name": self.order.organization.safe_translation_getter(
                        "title", language_code=self.definition.language
                    ),
                    "address": AddressSerializer(organization_address).data,
                    "representative": self.order.organization.representative,
                    "representative_profession": self.order.organization.representative_profession,
                    "enterprise_code": self.order.organization.enterprise_code,
                    "activity_category_code": self.order.organization.activity_category_code,
                    "signatory_representative": self.order.organization.signatory_representative,
                    "signatory_representative_profession": (
                        self.order.organization.signatory_representative_profession
                    ),
                    "contact_phone": self.order.organization.contact_phone,
                    "contact_email": self.order.organization.contact_email,
                    "dpo_email": self.order.organization.dpo_email,
                },
            }
        return None

    @factory.lazy_attribute
    def definition_checksum(self):
        """
        Lazily generate the definition_checksum from context.
        """
        if self.student_signed_on or self.submitted_for_signature_on:
            return hashlib.sha256(
                json.dumps(self.context, sort_keys=True).encode("utf-8")
            ).hexdigest()
        return None

    @factory.lazy_attribute
    def signature_backend_reference(self):
        """
        Define signature_backend_reference as dummy signature backend
        """
        if self.student_signed_on or self.submitted_for_signature_on:
            return f"wfl_fake_dummy_demo_dev_{uuid.uuid4()}"

        return None


class SiteFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """Factory for the Site model"""

    name = factory.Sequence(lambda n: f"Site {n:03d}")
    domain = factory.Faker("domain_name")

    class Meta:
        model = Site


class SiteConfigFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """Factory for the Site Config model"""

    site = factory.SubFactory(SiteFactory)

    class Meta:
        model = models.SiteConfig


class ActivityLogFactory(DebugModelFactory, factory.django.DjangoModelFactory):
    """Factory for the ActivityLog model"""

    class Meta:
        model = models.ActivityLog

    user = factory.SubFactory(UserFactory)
    level = factory.fuzzy.FuzzyChoice(
        [level[0] for level in enums.ACTIVITY_LOG_LEVEL_CHOICES]
    )
    created_on = factory.Faker("date_time_this_year")
    type = factory.fuzzy.FuzzyChoice(
        [event_type[0] for event_type in enums.ACTIVITY_LOG_TYPE_CHOICES]
    )

    @factory.lazy_attribute
    def context(self):
        """
        Generate the activity log context depending on the type.
        """
        if self.type == enums.ACTIVITY_LOG_TYPE_NOTIFICATION:
            return {}
        if self.type in [
            enums.ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
            enums.ACTIVITY_LOG_TYPE_PAYMENT_FAILED,
            enums.ACTIVITY_LOG_TYPE_PAYMENT_REFUNDED,
        ]:
            return {"order_id": str(factory.Faker("uuid4"))}
        return {}


class SkillFactory(factory.django.DjangoModelFactory):
    """Factory for the Skill model"""

    class Meta:
        model = models.Skill

    title = factory.Faker("word")


class TeacherFactory(factory.django.DjangoModelFactory):
    """Factory for the Teacher model"""

    class Meta:
        model = models.Teacher

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
