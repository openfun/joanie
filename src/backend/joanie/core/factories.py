"""
Core application factories
"""
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone

import factory
import factory.fuzzy
import pytz

from . import enums, models


class CertificateDefinitionFactory(factory.django.DjangoModelFactory):
    """A factory to create a certificate definition"""

    class Meta:
        model = models.CertificateDefinition

    title = factory.Sequence(lambda n: "Certificate definition %s" % n)
    name = factory.Sequence(lambda n: "certificate-definition-%s" % n)


class OrganizationFactory(factory.django.DjangoModelFactory):
    """A factory to create an organization"""

    class Meta:
        model = models.Organization

    code = factory.Faker("ean", length=8)
    title = factory.Sequence(lambda n: "Organization %s" % n)


class CourseFactory(factory.django.DjangoModelFactory):
    """A factory to create a course"""

    class Meta:
        model = models.Course

    code = factory.Faker("ean", length=8)
    title = factory.Sequence(lambda n: "Course %s" % n)
    organization = factory.SubFactory(OrganizationFactory)


class CourseRunFactory(factory.django.DjangoModelFactory):
    """
    A factory to easily generate a credible course run for our tests.
    """

    class Meta:
        model = models.CourseRun

    course = factory.SubFactory(CourseFactory)
    resource_link = factory.Faker("uri")
    title = factory.Sequence(lambda n: "Course run %s" % n)

    @factory.lazy_attribute
    def start(self):  # pylint: disable=no-self-use
        """
        A start datetime for the course run is chosen randomly in the future (it can
        of course be forced if we want something else), then the other significant dates
        for the course run are chosen randomly in periods that make sense with this start date.
        """
        now = timezone.now()
        period = timedelta(days=200)
        return datetime.utcfromtimestamp(
            random.randrange(  # nosec
                int((now - period).timestamp()), int((now + period).timestamp())
            )
        ).replace(tzinfo=pytz.utc)

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
        ).replace(tzinfo=pytz.utc)

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
        ).replace(tzinfo=pytz.utc)

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
        ).replace(tzinfo=pytz.utc)


class ProductFactory(factory.django.DjangoModelFactory):
    """A factory to create a product"""

    class Meta:
        model = models.Product

    type = enums.PRODUCT_TYPE_ENROLLMENT
    title = factory.Faker("bs")
    call_to_action = "let's go!"
    course = factory.SubFactory(CourseFactory)
    price = factory.LazyAttribute(lambda _: random.randint(0, 100))  # nosec

    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def target_courses(self, create, extracted, **kwargs):
        """
        Link target courses to the product after its creation:
        - link the list of courses passed in "extracted" if any
        - otherwise, generate a random batch of 3 courses and link them
        """
        if not extracted:
            extracted = CourseFactory.create_batch(3)

        for course in extracted:
            ProductCourseRelationFactory(product=self, course=course)


class ProductCourseRelationFactory(factory.django.DjangoModelFactory):
    """A factory to create ProductCourseRelation object"""

    class Meta:
        model = models.ProductCourseRelation

    product = factory.SubFactory(ProductFactory)
    course = factory.SubFactory(CourseFactory)
    position = factory.fuzzy.FuzzyInteger(0, 1000)


class UserFactory(factory.django.DjangoModelFactory):
    """
    A factory to create an authenticated user for joanie side
    (to manage objects on admin interface)
    """

    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = make_password("password")


class OrderFactory(factory.django.DjangoModelFactory):
    """A factory to create an Order"""

    class Meta:
        model = models.Order

    product = factory.SubFactory(ProductFactory)
    owner = factory.SubFactory(UserFactory)
    state = factory.fuzzy.FuzzyChoice([s[0] for s in enums.ORDER_STATE_CHOICES])


    @factory.post_generation
    # pylint: disable=unused-argument,no-member
    def target_courses(self, create, extracted, **kwargs):
        """
        Link courses to the order after its creation:
        - link the list of courses passed in "extracted" if any
        - otherwise, link to the courses pointed by the related product
        """
        if not extracted:
            extracted = self.product.target_courses.all()

        for course in extracted:
            OrderCourseRelationFactory(order=self, course=course)


class OrderCourseRelationFactory(factory.django.DjangoModelFactory):
    """A factory to create OrderCourseRelation object"""

    class Meta:
        model = models.OrderCourseRelation

    order = factory.SubFactory(OrderFactory)
    course = factory.SubFactory(CourseFactory)
    position = factory.fuzzy.FuzzyInteger(0, 1000)


class AddressFactory(factory.django.DjangoModelFactory):
    """A factory to create an user address"""

    class Meta:
        model = models.Address

    name = factory.fuzzy.FuzzyChoice(["Home", "Office"])
    address = factory.Faker("street_address")
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    owner = factory.SubFactory(UserFactory)
