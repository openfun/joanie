"""Test suite for the organization access serializer"""
import random

from django.test import TestCase

from rest_framework import exceptions

from joanie.core import factories, models, serializers


class OrganizationAccessSerializerTestCase(TestCase):
    """Organization access serializer test case"""

    def test_serializers_organization_access_no_request_no_organization(self):
        """
        The organization access serializer should return a 400 if "organization_id"
        is not passed in context.
        """
        user = factories.UserFactory()

        data = {
            "user": str(user.id),
            "role": random.choice(models.OrganizationAccess.ROLE_CHOICES)[0],
        }
        serializer = serializers.OrganizationAccessSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        message = "You must set a organization ID in context to create a new organization access."
        self.assertEqual(
            serializer.errors,
            {"non_field_errors": [message]},
        )

    def test_serializers_organization_access_no_request_with_organization(self):
        """
        The organization access serializer should raise a permission error even if a
        "organization_id" is passed if there is no request, so no authorized user.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()

        data = {
            "user": str(user.id),
            "role": random.choice(models.OrganizationAccess.ROLE_CHOICES)[0],
        }
        serializer = serializers.OrganizationAccessSerializer(
            data=data, context={"organization_id": str(organization.id)}
        )

        with self.assertRaises(exceptions.PermissionDenied):
            self.assertTrue(serializer.is_valid())
