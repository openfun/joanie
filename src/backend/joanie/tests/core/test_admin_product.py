"""
Test suite for products admin pages
"""

import random
import uuid
from http import HTTPStatus

from django.conf import settings
from django.urls import reverse

import lxml.html

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class ProductAdminTestCase(BaseAPITestCase):
    """Test suite for admin to manipulate products."""

    def test_admin_product_create_forbidden(self):
        """A user with not enough permissions should not be allowed to create a product."""
        # Log in a user without permission
        user = factories.UserFactory(is_staff=True)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            reverse("admin:core_product_add"),
            data={
                "type": "enrollment",
                "title": "Product for course",
                "call_to_action": "Let's go",
                "target_course_relations-TOTAL_FORMS": 0,
                "target_course_relations-INITIAL_FORMS": 0,
            },
        )
        self.assertEqual(models.Product.objects.count(), 0)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_admin_product_create_success_enrollment(self):
        """A user with permissions should be able to create a product of type enrollment."""
        organization = factories.OrganizationFactory()
        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'enrollment' so without certificate definition
        data = {
            "type": "enrollment",
            "title": "My product",
            "call_to_action": "Let's go",
            "organizations": str(organization.id),
            "offering_rules-TOTAL_FORMS": 0,
            "offering_rules-INITIAL_FORMS": 0,
            "target_course_relations-TOTAL_FORMS": 0,
            "target_course_relations-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("admin:core_product_add"), data=data)

        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 1)

        product = models.Product.objects.get()
        self.assertEqual(list(product.courses.all()), [])
        self.assertEqual(product.type, "enrollment")
        self.assertEqual(product.title, "My product")
        self.assertEqual(product.call_to_action, "Let's go")

    def test_admin_product_create_with_certificate_and_bad_type_product(self):
        """
        It should not be allowed to specify a certificate definition for products of
        type enrollment.
        """
        certificate_definition = factories.CertificateDefinitionFactory()

        # Log in a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # now try to create a product with certificate definition for a product with bad type
        response = self.client.post(
            reverse("admin:core_product_add"),
            data={
                "type": "enrollment",
                "title": "Product for course",
                "call_to_action": "Let's go",
                "certificate_definition": certificate_definition.pk,
            },
        )
        self.assertEqual(models.Product.objects.count(), 0)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "errorlist")
        self.assertContains(
            response,
            "Certificate definition is only allowed for product kinds: certificate, credential",
        )

    def test_admin_product_create_success_certificate(self):
        """
        It should be allowed to specify a certificate definition for products of
        type "certificate" or "credential".
        """
        organization = factories.OrganizationFactory()
        certificate_definition = factories.CertificateDefinitionFactory()

        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'credential' so with certificate definition
        product_type = random.choice(["certificate", "credential"])
        data = {
            "type": product_type,
            "title": "Product for course",
            "call_to_action": "Let's go",
            "certificate_definition": certificate_definition.pk,
            "organizations": str(organization.id),
            "offering_rules-TOTAL_FORMS": 0,
            "offering_rules-INITIAL_FORMS": 0,
            "target_course_relations-TOTAL_FORMS": 0,
            "target_course_relations-INITIAL_FORMS": 0,
        }

        response = self.client.post(
            reverse("admin:core_product_add"),
            data=data,
        )
        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 1)

        product = models.Product.objects.get()
        self.assertEqual(product.certificate_definition, certificate_definition)
        self.assertEqual(product.type, product_type)
        self.assertEqual(product.title, "Product for course")
        self.assertEqual(product.call_to_action, "Let's go")

    def test_admin_product_create_id_read_only(self):
        """The id field should be readonly"""
        organization = factories.OrganizationFactory()
        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'credential' so with certificate definition
        data = {
            "id": "my-uid",
            "type": "credential",
            "title": "Product for course",
            "call_to_action": "Let's go",
            "organizations": str(organization.id),
            "offering_rules-TOTAL_FORMS": 0,
            "offering_rules-INITIAL_FORMS": 0,
            "target_course_relations-TOTAL_FORMS": 0,
            "target_course_relations-INITIAL_FORMS": 0,
        }

        response = self.client.post(
            reverse("admin:core_product_add"),
            data=data,
        )

        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 1)

        product = models.Product.objects.get()
        self.assertNotEqual(product.id, data["id"])
        self.assertEqual(len(str(product.id)), 36)
        self.assertEqual(type(product.id), uuid.UUID)

    def test_admin_product_allow_sorting_targeted_courses(self):
        """
        It should be possible to manage target courses directly from product
        admin change view.
        """
        organization = factories.OrganizationFactory()

        # Create courses
        [course, *target_courses] = factories.CourseFactory.create_batch(4)

        # Create a product
        product = factories.ProductFactory(
            courses=[course], target_courses=target_courses
        )

        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we go to the product admin change view
        response = self.client.get(
            reverse("admin:core_product_change", args=(product.pk,)),
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, product.title)

        # - Check that there is a sortable product target course relation section
        html = lxml.html.fromstring(response.content)

        sortable_section = html.cssselect(".sortable")[0]
        self.assertIsNotNone(sortable_section)

        section_title = sortable_section.cssselect("h2")[0]
        self.assertEqual(
            section_title.text_content(),
            "Target courses relations to products with a position",
        )

        sortable_courses = sortable_section.cssselect(".form-row.has_original")
        self.assertEqual(len(sortable_courses), 3)

        [tc0, tc1, tc2] = product.target_courses.all().order_by(
            "product_target_relations"
        )
        self.assertEqual(tc0, target_courses[0])
        self.assertEqual(tc1, target_courses[1])
        self.assertEqual(tc2, target_courses[2])

        # - Invert targeted courses position
        data = {
            "type": product.type,
            "title": product.title,
            "description": product.description,
            "price_0": product.price,
            "price_1": settings.DEFAULT_CURRENCY,
            "call_to_action": product.call_to_action,
            "organizations": str(organization.id),
            "offering_rules-TOTAL_FORMS": 0,
            "offering_rules-INITIAL_FORMS": 0,
            "target_course_relations-TOTAL_FORMS": 3,
            "target_course_relations-INITIAL_FORMS": 3,
            "target_course_relations-0-id": tc2.product_target_relations.get(
                product=product
            ).pk,
            "target_course_relations-0-product": product.pk,
            "target_course_relations-0-position": 0,
            "target_course_relations-0-course": tc2.pk,
            "target_course_relations-1-id": tc1.product_target_relations.get(
                product=product
            ).pk,
            "target_course_relations-1-product": product.pk,
            "target_course_relations-1-position": 1,
            "target_course_relations-1-course": tc1.pk,
            "target_course_relations-2-id": tc0.product_target_relations.get(
                product=product
            ).pk,
            "target_course_relations-2-product": product.pk,
            "target_course_relations-2-position": 2,
            "target_course_relations-2-course": tc0.pk,
        }

        response = self.client.post(
            reverse(
                "admin:core_product_change",
                args=(product.pk,),
            ),
            data=data,
        )

        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        product.refresh_from_db()
        [tc0, tc1, tc2] = product.target_courses.all().order_by(
            "product_target_relations"
        )
        self.assertEqual(tc0, target_courses[2])
        self.assertEqual(tc1, target_courses[1])
        self.assertEqual(tc2, target_courses[0])

    def test_admin_product_should_display_related_course_links(self):
        """
        Product admin view should display a read only field "related courses"
        in charge of listing related courses with a link to the course admin
        change view
        """

        # Create courses
        courses = factories.CourseFactory.create_batch(2)

        # Create a product
        product = factories.ProductFactory(courses=courses)

        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we go to the product admin change view
        response = self.client.get(
            reverse("admin:core_product_change", args=(product.pk,)),
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, product.title)

        # - Check there are links to go to related courses admin change view
        tree = lxml.html.fromstring(response.content)
        links = tree.xpath(
            '//div[contains(@class, "field-related_courses")]//a[not(contains(@class, "button"))]'
        )

        # - Product courses are ordered by code
        [course_0, course_1] = product.courses.all()

        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].text_content(), f"{course_0.code} | {course_0.title}")
        self.assertEqual(
            links[0].attrib["href"],
            reverse("admin:core_course_change", args=(course_0.pk,)),
        )
        self.assertEqual(links[1].text_content(), f"{course_1.code} | {course_1.title}")
        self.assertEqual(
            links[1].attrib["href"],
            reverse("admin:core_course_change", args=(course_1.pk,)),
        )

    def test_admin_product_should_allow_to_generate_certificate_for_related_course(
        self,
    ):
        """
        Product admin view should display a link to generate certificates for
        the couple course - product next to each related course item. This link is
        displayed only for certifying products.
        """

        # Create a course
        course = factories.CourseFactory()

        # Create a product
        product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )

        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we go to the product admin change view
        response = self.client.get(
            reverse("admin:core_product_change", args=(product.pk,)),
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, product.title)

        # - Check there are links to go to related courses admin change view
        html = lxml.html.fromstring(response.content)
        related_courses_field = html.cssselect(".field-related_courses")[0]

        # - The related course should be displayed
        related_course = related_courses_field.cssselect("li")
        self.assertEqual(len(related_course), 1)
        # - And it should contain one link
        links = related_course[0].cssselect("a")
        self.assertEqual(len(links), 1)
        # - 1st a link to go to the related course change view
        self.assertEqual(links[0].text_content(), f"{course.code} | {course.title}")
        self.assertEqual(
            links[0].attrib["href"],
            reverse("admin:core_course_change", args=(course.pk,)),
        )

    def test_admin_product_use_translatable_change_form_with_actions_template(self):
        """
        The product admin change view should use a custom change form template
        to display both translation tabs of django parler and action buttons of
        django object actions.
        """
        # Create a product
        product = factories.ProductFactory()

        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we go to the product admin change view
        with self.assertTemplateUsed(
            "joanie/admin/translatable_change_form_with_actions.html"
        ):
            self.client.get(
                reverse("admin:core_product_change", args=(product.pk,)),
            )
