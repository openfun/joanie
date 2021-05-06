"""
Test suite for products API
"""
import random
import uuid

from django.urls import reverse

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
