"""Test suite for delete_user task"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from joanie.badges import factories as badges_factories
from joanie.badges import models as badges_models
from joanie.core import factories, models
from joanie.core.enums import ORDER_STATE_COMPLETED
from joanie.core.tasks.delete_user import delete_user
from joanie.payment import models as payment_models
from joanie.tests.base import BaseLogMixinTestCase


class DeleteUserTasksTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for delete_user task
    """

    def test_delete_user(self):
        """Test delete_user task"""
        factories.UserFactory(username="test_user")

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
        user = factories.UserFactory(username="test_user")
        factories.OrderGeneratorFactory(owner=user, state=ORDER_STATE_COMPLETED)

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
        the access should be deleted but not the organization.
        """
        user = factories.UserFactory(username="test_user")
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        factories.UserOrganizationAccessFactory.create_batch(
            3, organization=organization
        )

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

    def test_delete_user_having_activity_logs(self):
        """
        When a user have activity logs, deleting it should also delete all related activity logs.
        """
        user = factories.UserFactory(username="test_user")
        factories.ActivityLogFactory.create_batch(3, user=user)
        factories.ActivityLogFactory.create_batch(4)

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.ActivityLog.objects.count(), 7)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.ActivityLog.objects.count(), 4)
        self.assertLogsContains(logger, "User test_user has been deleted.")

    def test_delete_user_having_issued_badges(self):
        """
        When a user have issued badges, deleting it should also delete all related issued
        badges.
        """
        user = factories.UserFactory(username="test_user")
        badge = badges_factories.BadgeFactory()
        badges_factories.IssuedBadgeFactory.create_batch(3, user=user, badge=badge)
        badges_factories.IssuedBadgeFactory.create_batch(4, badge=badge)

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(badges_models.IssuedBadge.objects.count(), 7)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(badges_models.IssuedBadge.objects.count(), 4)
        self.assertLogsContains(logger, "User test_user has been deleted.")

    def test_delete_user_having_course_accesses(self):
        """
        When a user have course accesses, deleting it should also delete all related course
        accesses.
        """
        user = factories.UserFactory(username="test_user")
        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(user=user, course=course)
        factories.UserCourseAccessFactory.create_batch(4, course=course)

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.CourseAccess.objects.count(), 5)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.CourseAccess.objects.count(), 4)
        self.assertLogsContains(logger, "User test_user has been deleted.")

    def test_delete_user_having_course_wishes(self):
        """
        When a user have course wishes, deleting it should also delete all related course wishes.
        """
        user = factories.UserFactory(username="test_user")
        course = factories.CourseFactory()
        factories.CourseWishFactory(owner=user, course=course)
        factories.CourseWishFactory.create_batch(4, course=course)

        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.CourseWish.objects.count(), 5)

        with self.assertLogs() as logger:
            delete_user("test_user")

        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())
        self.assertEqual(models.CourseWish.objects.count(), 4)
        self.assertLogsContains(logger, "User test_user has been deleted.")
