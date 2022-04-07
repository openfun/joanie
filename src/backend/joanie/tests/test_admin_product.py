"""
Test suite for products API
"""
import random
import uuid
from unittest import mock

from django.urls import reverse

import lxml.html

from joanie.core import factories, models

from .base import BaseAPITestCase


class ProductAdminTestCase(BaseAPITestCase):
    """Test suite for API to manipulate products."""

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
        change view.
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

    @mock.patch.object(models.Order, "cancel")
    def test_admin_order_action_cancel(self, mock_cancel):
        """
        Order admin should display an action to cancel an order which call
        order.cancel method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        order = factories.OrderFactory()
        self.client.login(username=user.username, password="password")
        order_changelist_page = reverse("admin:core_order_changelist")
        response = self.client.get(order_changelist_page)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancel selected orders")

        # - Trigger "cancel" action
        self.client.post(
            order_changelist_page, {"action": "cancel", "_selected_action": order.pk}
        )
        self.assertEqual(response.status_code, 200)
        mock_cancel.assert_called_once_with()
