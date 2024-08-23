"""Test suite for delete_user task"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from joanie.core import models
from joanie.core.enums import ORDER_STATE_COMPLETED
from joanie.core.factories import (
    OrderGeneratorFactory,
    OrganizationFactory,
    UserFactory,
    UserOrganizationAccessFactory,
)
from joanie.core.tasks.delete_user import delete_user
from joanie.payment import models as payment_models
from joanie.tests.base import BaseLogMixinTestCase


class DeleteUserTasksTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for delete_user task
    """

    def test_delete_user(self):
        """Test delete_user task"""
        UserFactory(username="test_user")

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertLogsContains(logger, "User test_user has been deleted.")

    def test_delete_user_not_found(self):
        """Test delete_user task with user not found"""
        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertLogsContains(logger, "User test_user does not exist.")
        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())

    def test_delete_user_with_related_order(self):
        """Test delete_user task with related order should delete everything in cascade."""
        self.assertEqual(get_user_model().objects.count(), 0)
        user = UserFactory(username="test_user")
        OrderGeneratorFactory(owner=user, state=ORDER_STATE_COMPLETED)

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        self.assertTrue(models.Address.objects.filter(owner=user).exists())
        self.assertEqual(models.Order.objects.count(), 1)
        self.assertEqual(payment_models.CreditCard.objects.count(), 1)
        self.assertEqual(payment_models.Invoice.objects.count(), 1)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(payment_models.CreditCard.objects.count(), 0)
        self.assertEqual(payment_models.Invoice.objects.count(), 0)
        self.assertFalse(models.Address.objects.filter(owner=user).exists())
        self.assertLogsContains(logger, "User test_user has been deleted.")

    def test_delete_user_having_access_to_an_organization(self):
        """
        When a user has access to an organization and we want to delete it,
        the access should be deleted but not the orgnization.
        """
        user = UserFactory(username="test_user")
        organization = OrganizationFactory()
        UserOrganizationAccessFactory(user=user, organization=organization)
        UserOrganizationAccessFactory.create_batch(3, organization=organization)

        self.assertEqual(get_user_model().objects.count(), 4)
        self.assertEqual(models.Organization.objects.count(), 1)
        self.assertEqual(models.OrganizationAccess.objects.count(), 4)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(get_user_model().objects.count(), 3)
        self.assertEqual(models.Organization.objects.count(), 1)
        self.assertEqual(models.OrganizationAccess.objects.count(), 3)
        self.assertLogsContains(logger, "User test_user has been deleted.")
