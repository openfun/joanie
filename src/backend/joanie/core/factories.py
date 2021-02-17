import datetime
import random
from slugify import slugify

import factory

from django.utils import timezone

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
    resource_link = factory.Faker("uri")
    title = factory.Sequence(lambda n: "Course run %s" % n)
    start = factory.LazyAttribute(
        lambda _: timezone.now() + datetime.timedelta(days=random.randint(0, 10)),
    )
    end = factory.LazyAttribute(
        lambda _: timezone.now() + datetime.timedelta(days=15+random.randint(0, 10)),
    )

    class Meta:
        model = models.CourseRun


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


class CourseProductCertificationFactory(factory.django.DjangoModelFactory):
    course_product = factory.SubFactory(CourseProductFactory)
    certificate_definition = factory.SubFactory(CertificateDefinitionFactory)

    class Meta:
        model = models.CourseProductCertification
