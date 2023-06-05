"""Test suite for the management command 'create_demo'"""
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from joanie.core import models
from joanie.demo import defaults
from joanie.payment import models as payment_models

TEST_NB_OBJECTS = {
    "organizations": 3,
    "products": 3,
    "courses": 3,
    "users": 5,
    "enrollments": 10,
    "max_orders_per_product": 3,
}


class CreateDemoTestCase(TestCase):
    """Test case for the management command 'create_demo'"""

    @override_settings(DEBUG=True)
    @mock.patch.dict(defaults.NB_OBJECTS, TEST_NB_OBJECTS)
    def test_commands_create_demo(self):
        """The create_demo management command should create objects as expected."""
        call_command("create_demo")

        nb_users = models.User.objects.count()
        self.assertEqual(nb_users, 5)
        self.assertEqual(models.Organization.objects.count(), 3)

        self.assertEqual(models.Product.objects.count(), 3)
        self.assertEqual(models.Course.objects.count(), 6)
        self.assertGreaterEqual(models.CourseRun.objects.count(), 3)
        self.assertEqual(models.CertificateDefinition.objects.count(), 3)
        self.assertGreaterEqual(models.ProductTargetCourseRelation.objects.count(), 3)
        self.assertEqual(models.CourseProductRelation.objects.count(), 3)
        self.assertGreaterEqual(models.Order.objects.count(), 3)

        product_target_counts = {
            p.id: p.target_courses.count() for p in models.Product.objects.all()
        }
        order_target_count = sum(
            product_target_counts[o.product.id] for o in models.Order.objects.all()
        )
        self.assertEqual(
            models.OrderTargetCourseRelation.objects.count(), order_target_count
        )

        nb_buyers = models.User.objects.filter(orders__isnull=False).distinct().count()
        self.assertGreaterEqual(models.Address.objects.count(), nb_buyers)
        self.assertGreaterEqual(payment_models.CreditCard.objects.count(), nb_buyers)
