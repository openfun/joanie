"""
Core application factories
"""
import random
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone as django_timezone

import factory.fuzzy
from djmoney.money import Money
from faker import Faker

from . import enums, models


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

    username = UniqueFaker("user_name")
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

    code = factory.Faker("ean", length=8)
    title = factory.Sequence(lambda n: f"Organization {n}")
    signature = factory.django.ImageField(
        filename="signature.png", format="png", width=1, height=1
    )
    logo = factory.django.ImageField(
        filename="logo.png", format="png", width=1, height=1
    )


class CourseFactory(factory.django.DjangoModelFactory):
    """A factory to create a course"""

    class Meta:
        model = models.Course

    code = factory.Faker("ean", length=8)
    title = factory.Sequence(lambda n: f"Course {n}")

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


class CourseRunFactory(factory.django.DjangoModelFactory):
    """
    A factory to easily generate a credible course run for our tests.
    """

    class Meta:
        model = models.CourseRun

    course = factory.SubFactory(CourseFactory)
    resource_link = factory.Faker("uri")
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

    @factory.lazy_attribute
    def start(self):  # pylint: disable=no-self-use
        """
        A start datetime for the course run is chosen randomly in the future (it can
        of course be forced if we want something else), then the other significant dates
        for the course run are chosen randomly in periods that make sense with this start date.
        """
        now = django_timezone.now()
        period = timedelta(days=200)
        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int((now - period).timestamp()), int((now + period).timestamp())
            )
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def end(self):
        """
        The end datetime is at a random duration after the start datetme (we pick within 90 days).
        """
        if not self.start:
            return None
        period = timedelta(days=90)
        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int(self.start.timestamp()), int((self.start + period).timestamp())
            )
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def enrollment_start(self):
        """
        The start of enrollment is a random datetime before the start datetime.
        """
        if not self.start:
            return None
        period = timedelta(days=90)
        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int((self.start - period).timestamp()), int(self.start.timestamp())
            )
        ).replace(tzinfo=timezone.utc)

    @factory.lazy_attribute
    def enrollment_end(self):
        """
        The end of enrollment is a random datetime between the start of enrollment
        and the end of the course.
        If the enrollment start and end datetimes have been forced to incoherent dates,
        then just don't set any end of enrollment...
        """
        if not self.start:
            return None
        enrollment_start = self.enrollment_start or self.start - timedelta(
            days=random.randint(1, 90)  # nosec
        )
        max_enrollment_end = self.end or self.start + timedelta(
            days=random.randint(1, 90)  # nosec
        )
        max_enrollment_end = max(
            enrollment_start + timedelta(hours=1), max_enrollment_end
        )
        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int(enrollment_start.timestamp()), int(max_enrollment_end.timestamp())
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

    type = enums.PRODUCT_TYPE_ENROLLMENT
    title = factory.Faker("bs")
    call_to_action = "let's go!"

    @factory.lazy_attribute
    # pylint: disable=no-self-use
    def price(self):
        """
        Return a Money object with a random amount and a random currency from
        the list of currencies supported by the application.
        """
        return Money(
            amount=Faker().pydecimal(left_digits=3, right_digits=2, min_value=0),
            currency=random.choice(settings.CURRENCIES),  # nosec
        )

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def courses(self, create, extracted, **kwargs):
        """
        Link courses to the product after its creation:
        - link the list of courses passed in "extracted" if any
        - otherwise create a random course and link it
        """
        if extracted is None:
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
        if not extracted:
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


class OrderFactory(factory.django.DjangoModelFactory):
    """A factory to create an Order"""

    class Meta:
        model = models.Order

    product = factory.SubFactory(ProductFactory)
    course = factory.LazyAttribute(lambda o: o.product.courses.order_by("?").first())
    owner = factory.SubFactory(UserFactory)

    @factory.lazy_attribute
    def organization(self):
        """Retrieve the organization from the product/course relation."""
        return (
            self.product.course_relations.get(course=self.course)
            .organizations.order_by("?")
            .first()
        )


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


class CertificateFactory(factory.django.DjangoModelFactory):
    """A factory to create a certificate"""

    class Meta:
        model = models.Certificate

    order = factory.SubFactory(
        OrderFactory,
        product__type=enums.PRODUCT_TYPE_CERTIFICATE,
    )

    @factory.lazy_attribute
    def certificate_definition(self):
        """
        Return the order product certificate definition.
        """
        return self.order.product.certificate_definition


class CourseWishFactory(factory.django.DjangoModelFactory):
    """A factory to create an user wish"""

    class Meta:
        model = models.CourseWish

    course = factory.SubFactory(CourseFactory)
    owner = factory.SubFactory(UserFactory)


class NotificationFactory(factory.django.DjangoModelFactory):
    """A factory to create an user wish"""

    class Meta:
        model = models.Notification
        exclude = ['notif_subject, notif_object']

    owner = factory.SubFactory(UserFactory)

    notif_subject_id = factory.SelfAttribute('notif_subject.id')
    notif_subject_ctype = factory.LazyAttribute(lambda o: ContentType.objects.get_for_model(o.notif_subject))

    notif_object_id = factory.SelfAttribute('notif_object.id')
    notif_object_ctype = factory.LazyAttribute(lambda o: ContentType.objects.get_for_model(o.notif_object))
