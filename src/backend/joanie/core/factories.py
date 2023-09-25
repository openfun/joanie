"""
Core application factories
"""
import random
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone as django_timezone

import factory.fuzzy
from easy_thumbnails.files import ThumbnailerImageFieldFile, generate_all_aliases
from faker import Faker

from joanie.core.models import CourseState

from . import enums, models


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


class UserFactory(factory.django.DjangoModelFactory):
    """
    A factory to create an authenticated user for joanie side
    (to manage objects on admin interface)
    """

    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f"user{n!s}")
    email = factory.Faker("email")
    language = factory.fuzzy.FuzzyChoice([lang[0] for lang in settings.LANGUAGES])
    password = make_password("password")


class CertificateDefinitionFactory(factory.django.DjangoModelFactory):
    """A factory to create a certificate definition"""

    class Meta:
        model = models.CertificateDefinition

    title = factory.Sequence(lambda n: f"Certificate definition {n}")
    name = factory.Sequence(lambda n: f"certificate-definition-{n}")
    template = settings.MARION_CERTIFICATE_DOCUMENT_ISSUER


class OrganizationFactory(factory.django.DjangoModelFactory):
    """A factory to create an organization"""

    class Meta:
        model = models.Organization

    code = factory.Sequence(lambda n: n)
    title = factory.Sequence(lambda n: f"Organization {n}")
    signature = factory.django.ImageField(
        filename="signature.png", format="png", width=1, height=1
    )
    logo = factory.django.ImageField(
        filename="logo.png", format="png", width=1, height=1
    )

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """
        Generate thumbnails for logo after organization has been created.
        """
        if create:
            generate_thumbnails_for_field(instance.logo)

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


class UserOrganizationAccessFactory(factory.django.DjangoModelFactory):
    """Create fake organization user accesses for testing."""

    class Meta:
        model = models.OrganizationAccess

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.fuzzy.FuzzyChoice(
        [r[0] for r in models.OrganizationAccess.ROLE_CHOICES]
    )


class CourseFactory(factory.django.DjangoModelFactory):
    """A factory to create a course"""

    class Meta:
        model = models.Course

    code = factory.Sequence(lambda k: f"{k:05d}")
    title = factory.Sequence(lambda n: f"Course {n}")
    cover = factory.django.ImageField(
        filename="cover.png", format="png", width=1, height=1
    )

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """
        Generate thumbnails for cover after course has been created.
        """
        if create:
            generate_thumbnails_for_field(instance.cover)

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


class UserCourseAccessFactory(factory.django.DjangoModelFactory):
    """Create fake course user accesses for testing."""

    class Meta:
        model = models.CourseAccess

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.fuzzy.FuzzyChoice([r[0] for r in models.CourseAccess.ROLE_CHOICES])


class CourseRunFactory(factory.django.DjangoModelFactory):
    """
    A factory to easily generate a credible course run for our tests.
    """

    class Params:
        """Parameters for the factory."""

        state = None
        ref_date = factory.LazyAttribute(lambda o: django_timezone.now())

    class Meta:
        model = models.CourseRun

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Course run {n}")

    # pylint: disable=no-self-use
    @factory.lazy_attribute
    def languages(self):
        """
        Compute a random set of languages from the complete list of Django supported languages.
        """
        return [
            language[0]
            for language in random.sample(
                enums.ALL_LANGUAGES, random.randint(1, 5)  # nosec
            )
        ]

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
        if self.state == CourseState.TO_BE_SCHEDULED:
            return None

        period = timedelta(
            days=random.randrange(1, 365, 1)  # nosec
        )  # between 1 and 365 days

        if self.state in [
            CourseState.ONGOING_OPEN,
            CourseState.ONGOING_CLOSED,
            CourseState.ARCHIVED_OPEN,
            CourseState.ARCHIVED_CLOSED,
        ]:
            # The course run is on going or archived,
            # so the start date must be less than the ref date
            min_date = self.ref_date - period
            max_date = self.ref_date
        elif self.state in [
            CourseState.FUTURE_OPEN,
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_CLOSED,
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
            random.randrange(  # nosec
                int(min_date.timestamp()), int(max_date.timestamp())
            )
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def end(self):
        """
        Compute the end date according to the course run state and the ref date.
        Otherwise, pick a random date in the range of 1 to 365 days after the start date
        """
        if not self.start:
            return None

        period = timedelta(
            days=random.randrange(1, 365, 1)  # nosec
        )  # between 1 and 365 days

        if self.state in [CourseState.ARCHIVED_OPEN, CourseState.ARCHIVED_CLOSED]:
            # The course run is archived, end date must be less than ref date
            if self.start >= self.ref_date:
                raise ValueError("Start date must be less than ref date.")
            min_date = self.start
            max_date = self.ref_date
        elif self.state in [CourseState.ONGOING_OPEN, CourseState.ONGOING_CLOSED]:
            # The course run is on going, end date must be greater than ref_date
            min_date = self.ref_date
            max_date = min_date + period
        elif self.state in [
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.FUTURE_CLOSED,
        ]:
            min_date = max(self.ref_date, self.start)
            max_date = min_date + period
        else:
            # Otherwise, we just want end date to be greater than start date
            min_date = self.start
            max_date = min_date + period

        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int(min_date.timestamp()), int(max_date.timestamp())
            )
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

        period = timedelta(
            days=random.randrange(1, 90, 1)  # nosec
        )  # between 1 and 90 days

        if self.state in [CourseState.FUTURE_OPEN, CourseState.FUTURE_CLOSED]:
            # The course run enrollment has not yet started,
            # so the enrollment start date must be less than the ref date
            min_date = self.ref_date - period
            max_date = self.ref_date
        elif self.state == CourseState.FUTURE_NOT_YET_OPEN:
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
            random.randrange(  # nosec
                int(min_date.timestamp()), int(max_date.timestamp())
            )
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
            or self.state == CourseState.ARCHIVED_OPEN
        ):
            # Archived open state is a special case.
            # The course run has ended but enrollment is still opened.
            return None

        period = timedelta(
            days=random.randrange(1, 90, 1)  # nosec
        )  # between 1 and 90 days

        if self.state in [CourseState.ONGOING_OPEN, CourseState.FUTURE_OPEN]:
            # The course run is opened for enrollment, so the enrollment end date must
            # be greater than the ref date and less than the course run end
            if self.end and self.end <= self.ref_date:
                raise ValueError("End date must be greater than ref date.")
            min_date = self.ref_date
            max_date = self.end or self.ref_date + period
        elif self.state in [CourseState.ONGOING_CLOSED, CourseState.FUTURE_CLOSED]:
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
            random.randrange(  # nosec
                int(min_date.timestamp()), int(max_date.timestamp())
            )
        ).replace(tzinfo=timezone.utc)


class EnrollmentFactory(factory.django.DjangoModelFactory):
    """A factory to create an enrollment"""

    class Meta:
        model = models.Enrollment

    course_run = factory.SubFactory(CourseRunFactory)
    user = factory.SubFactory(UserFactory)
    is_active = factory.fuzzy.FuzzyChoice([True, False])
    state = factory.fuzzy.FuzzyChoice([s[0] for s in enums.ENROLLMENT_STATE_CHOICES])


class ProductFactory(factory.django.DjangoModelFactory):
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
            CourseProductRelationFactory(product=self, course=course)

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

    @factory.lazy_attribute
    def certificate_definition(self):
        """
        Return a CertificateDefinition object with a random name and a random
        description if the product type allows to have a certificate.
        """
        if self.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED:
            return None

        return CertificateDefinitionFactory()


class CourseProductRelationFactory(factory.django.DjangoModelFactory):
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


class ProductTargetCourseRelationFactory(factory.django.DjangoModelFactory):
    """A factory to create ProductTargetCourseRelation object"""

    class Meta:
        model = models.ProductTargetCourseRelation
        skip_postgeneration_save = True

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


class OrderGroupFactory(factory.django.DjangoModelFactory):
    """A factory to create order groups."""

    class Meta:
        model = models.OrderGroup

    product = factory.SubFactory(ProductFactory)
    nb_seats = factory.fuzzy.FuzzyInteger(0, 100)


class OrderFactory(factory.django.DjangoModelFactory):
    """A factory to create an Order"""

    class Meta:
        model = models.Order

    product = factory.SubFactory(ProductFactory)
    course = factory.LazyAttribute(lambda o: o.product.courses.order_by("?").first())
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


class OrderTargetCourseRelationFactory(factory.django.DjangoModelFactory):
    """A factory to create OrderTargetCourseRelation object"""

    class Meta:
        model = models.OrderTargetCourseRelation

    order = factory.SubFactory(OrderFactory)
    course = factory.SubFactory(CourseFactory)
    position = factory.fuzzy.FuzzyInteger(0, 1000)


class AddressFactory(factory.django.DjangoModelFactory):
    """A factory to create an user address"""

    class Meta:
        model = models.Address

    title = factory.fuzzy.FuzzyChoice(["Home", "Office"])
    address = factory.Faker("street_address")
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    owner = factory.SubFactory(UserFactory)


class OrderCertificateFactory(factory.django.DjangoModelFactory):
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


class EnrollmentCertificateFactory(factory.django.DjangoModelFactory):
    """
    A factory to create a certificate directly related to an enrollment (not through an order)
    """

    class Meta:
        model = models.Certificate

    enrollment = factory.SubFactory(EnrollmentFactory)
    certificate_definition = factory.SubFactory(CertificateDefinitionFactory)
    organization = factory.SubFactory(OrganizationFactory)


class CourseWishFactory(factory.django.DjangoModelFactory):
    """A factory to create a course wish for a user."""

    class Meta:
        model = models.CourseWish

    course = factory.SubFactory(CourseFactory)
    owner = factory.SubFactory(UserFactory)
