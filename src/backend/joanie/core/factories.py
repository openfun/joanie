import random
from datetime import datetime, timedelta

from django.utils import timezone

import factory
import pytz
from slugify import slugify

from . import models


class CertificateDefinitionFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: "Certificate definition %s" % n)
    name = factory.Sequence(lambda n: "certificate-definition-%s" % n)

    class Meta:
        model = models.CertificateDefinition


class OrganizationFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "cms-reference-%s" % n)
    title = factory.Sequence(lambda n: "Organization %s" % n)

    class Meta:
        model = models.Organization


class CourseFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "cms-reference-%s" % n)
    title = factory.Sequence(lambda n: "Course %s" % n)
    organization = factory.SubFactory(OrganizationFactory)

    class Meta:
        model = models.Course


class CourseRunFactory(factory.django.DjangoModelFactory):
    """
    A factory to easily generate a credible course run for our tests.
    """

    class Meta:
        model = models.CourseRun

    resource_link = factory.Faker("uri")
    title = factory.Sequence(lambda n: "Course run %s" % n)

    @factory.lazy_attribute
    def start(self):
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
    title = factory.Sequence(lambda n: "Product %s" % n)
    name = factory.Sequence(lambda o: slugify(o.title))
    call_to_action_label = "let's go!"

    class Meta:
        model = models.Product


class CourseProductFactory(factory.django.DjangoModelFactory):
    product = factory.SubFactory(ProductFactory)
    course = factory.SubFactory(CourseFactory)
    price = factory.LazyAttribute(lambda _: random.randint(0, 100))

    class Meta:
        model = models.CourseProduct


class ProductCourseRunPositionFactory(factory.django.DjangoModelFactory):
    course_product = factory.SubFactory(CourseProductFactory)
    course_run = factory.SubFactory(CourseRunFactory)

    class Meta:
        model = models.ProductCourseRunPosition
