"""
Test suite for products admin pages
"""
import random
import uuid
from unittest import mock

from django.contrib.messages import get_messages
from django.urls import reverse

import lxml.html

from joanie.core import factories, models

from ..core import enums
from .base import BaseAPITestCase


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
                "course_relations-TOTAL_FORMS": 0,
                "course_relations-INITIAL_FORMS": 0,
            },
        )
        self.assertEqual(models.Product.objects.count(), 0)
        self.assertEqual(response.status_code, 403)

    def test_admin_product_create_success_enrollment(self):
        """A user with permissions should be able to create a product of type enrollment."""
        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'enrollment' so without certificate definition
        data = {
            "type": "enrollment",
            "title": "My product",
            "call_to_action": "Let's go",
            "course_relations-TOTAL_FORMS": 0,
            "course_relations-INITIAL_FORMS": 0,
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
        self.assertEqual(response.status_code, 200)
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
            "course_relations-TOTAL_FORMS": 0,
            "course_relations-INITIAL_FORMS": 0,
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

    def test_admin_product_create_uid_read_only(self):
        """The uid field should be readonly"""
        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'credential' so with certificate definition
        data = {
            "uid": "my-uid",
            "type": "credential",
            "title": "Product for course",
            "call_to_action": "Let's go",
            "course_relations-TOTAL_FORMS": 0,
            "course_relations-INITIAL_FORMS": 0,
        }

        response = self.client.post(
            reverse("admin:core_product_add"),
            data=data,
        )

        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 1)

        product = models.Product.objects.get()
        self.assertNotEqual(product.uid, data["uid"])
        self.assertEqual(len(str(product.uid)), 36)
        self.assertEqual(type(product.uid), uuid.UUID)

    def test_admin_product_allow_sorting_targeted_courses(self):
        """
        It should be possible to manage targeted courses directly from product
        admin change view.
        """

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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.title)

        # - Check that there is a sortable product course relation section
        html = lxml.html.fromstring(response.content)

        sortable_section = html.cssselect(".sortable")[0]
        self.assertIsNotNone(sortable_section)

        section_title = sortable_section.cssselect("h2")[0]
        self.assertEqual(
            section_title.text_content(),
            "Courses relations to products with a position",
        )

        sortable_courses = sortable_section.cssselect(".form-row.has_original")
        self.assertEqual(len(sortable_courses), 3)

        [tc0, tc1, tc2] = product.target_courses.all().order_by("product_relations")
        self.assertEqual(tc0, target_courses[0])
        self.assertEqual(tc1, target_courses[1])
        self.assertEqual(tc2, target_courses[2])

        # - Invert targeted courses position
        data = {
            "type": product.type,
            "title": product.title,
            "description": product.description,
            "price_0": product.price.amount,
            "price_1": product.price.currency,
            "call_to_action": product.call_to_action,
            "course_relations-TOTAL_FORMS": 3,
            "course_relations-INITIAL_FORMS": 3,
            "course_relations-0-id": tc2.product_relations.get(product=product).pk,
            "course_relations-0-product": product.pk,
            "course_relations-0-position": 0,
            "course_relations-0-course": tc2.pk,
            "course_relations-1-id": tc1.product_relations.get(product=product).pk,
            "course_relations-1-product": product.pk,
            "course_relations-1-position": 1,
            "course_relations-1-course": tc1.pk,
            "course_relations-2-id": tc0.product_relations.get(product=product).pk,
            "course_relations-2-product": product.pk,
            "course_relations-2-position": 2,
            "course_relations-2-course": tc0.pk,
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
        [tc0, tc1, tc2] = product.target_courses.all().order_by("product_relations")
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.title)

        # - Check there are links to go to related courses admin change view
        html = lxml.html.fromstring(response.content)
        related_courses_field = html.cssselect(".field-related_courses")[0]

        # - Product courses are ordered by code
        [course_0, course_1] = product.courses.all()

        links = related_courses_field.cssselect("a")
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.title)

        # - Check there are links to go to related courses admin change view
        html = lxml.html.fromstring(response.content)
        related_courses_field = html.cssselect(".field-related_courses")[0]

        # - The related course should be displayed
        related_course = related_courses_field.cssselect("li")
        self.assertEqual(len(related_course), 1)
        # - And it should contain two links
        links = related_course[0].cssselect("a")
        self.assertEqual(len(links), 2)
        # - 1st a link to go to the related course change view
        self.assertEqual(links[0].text_content(), f"{course.code} | {course.title}")
        self.assertEqual(
            links[0].attrib["href"],
            reverse("admin:core_course_change", args=(course.pk,)),
        )

        # - 2nd a link to generate certificate for the course - product couple
        self.assertEqual(links[1].text_content(), "Generate certificates")
        self.assertEqual(
            links[1].attrib["href"],
            reverse(
                "admin:generate_certificates",
                kwargs={"product_id": product.id, "course_code": course.code},
            ),
        )

    @mock.patch("joanie.core.helpers.generate_certificates_for_orders", return_value=0)
    def test_admin_product_generate_certificate_for_course(
        self, mock_generate_certificates
    ):
        """
        Product Admin should contain an endpoint which triggers the
        `create_certificates` management command with product and course as options.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])

        response = self.client.get(
            reverse(
                "admin:generate_certificates",
                kwargs={"course_code": course.code, "product_id": product.id},
            ),
        )

        # - Generate certificates command should have been called
        mock_generate_certificates.assert_called_once()

        # Check the presence of a confirmation message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "No certificates have been generated.")

        # - User should be redirected to the product change view
        self.assertRedirects(
            response, reverse("admin:core_product_change", args=(product.id,))
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
