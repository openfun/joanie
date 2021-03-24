"""
Test suite for products models
"""
import uuid

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from joanie.core import enums, factories, models


class ProductAdminTestCase(TestCase):
    """Test suite for Admin Product interface"""

    def setUp(self):
        translation.activate("en-us")
        self.course = factories.CourseFactory.create()
        self.certificate_definition = factories.CertificateDefinitionFactory.create()
        self.course_run1 = factories.CourseRunFactory.create()
        self.course_run2 = factories.CourseRunFactory.create()

    def _get_product_creation_data(self):
        return {
            "uid": uuid.uuid4(),
            "course": self.course.pk,
            "type": enums.PRODUCT_TYPE_ENROLLMENT,
            "course_runs": [self.course_run1.pk, self.course_run2.pk],
            "title": "Product for course",
            "call_to_action": "Let's go",
        }

    def test_create_product_forbidden(self):
        """Manage product not allowed to authenticated user with enough permission"""
        # Log in a user without permission
        user = factories.UserFactory(is_staff=True)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            reverse("admin:core_product_add"),
            data=self._get_product_creation_data(),
        )
        self.assertEqual(models.Product.objects.count(), 0)
        self.assertEqual(response.status_code, 403)

    def test_create_product_with_certificate_and_bad_type_product(self):
        """Do not allow certificate definition for products with type enrollment"""
        # Log in a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # now try to create a product with certificate definition for a product with bad type
        invalid_data = self._get_product_creation_data()
        invalid_data["certificate_definition"] = self.certificate_definition.pk
        response = self.client.post(
            reverse("admin:core_product_add"),
            data=invalid_data,
        )
        self.assertEqual(models.Product.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertContains(
            response,
            "Certificate definition is only allowed for product kinds: certificate, credential",
        )

    def test_create_product_success(self):
        """Allow certificate definition only for products with type credential or certificate"""
        # Login a user with all permission to manage products in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we create a product with type 'enrollment' so without certificate definition
        data = self._get_product_creation_data()
        response = self.client.post(reverse("admin:core_product_add"), data=data)
        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 1)

        # Now we create a product with type 'credential' so with certificate definition
        data = data.copy()
        data["type"] = enums.PRODUCT_TYPE_CREDENTIAL
        data["certificate_definition"] = self.certificate_definition.pk
        data["uid"] = uuid.uuid4()
        response = self.client.post(
            reverse("admin:core_product_add"),
            data=data,
        )
        self.assertRedirects(response, reverse("admin:core_product_changelist"))
        self.assertEqual(models.Product.objects.count(), 2)
