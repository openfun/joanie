"""Joanie core helpers tests suite"""
import random
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test.testcases import TestCase

from joanie.core import enums, factories, models
from joanie.core.utils import webhooks

# pylint: disable=too-many-locals,too-many-public-methods,too-many-lines


class NotificationsTestCase(TestCase):
    """Joanie core notifications tests case"""

    def test_course_wish_and_new_course_run_create_notification(self):
        user = factories.UserFactory()
        course = factories.CourseFactory()
        factories.CourseWishFactory.create(owner=user, course=course)

        factories.CourseRunFactory(course=course, is_listed=True)

        self.assertEqual(models.Notification.objects.count(), 1)

    def test_course_wish_and_new_target_course_in_product_create_notification(self):
        user = factories.UserFactory()
        course = factories.CourseFactory()
        factories.CourseWishFactory.create(owner=user, course=course)

        product = factories.ProductFactory()
        product.target_courses.add(course)
        product.save()

        self.assertEqual(models.Notification.objects.count(), 1)

    def test_course_wish_and_new_product_create_notification(self):
        user = factories.UserFactory()
        course = factories.CourseFactory()
        factories.CourseWishFactory.create(owner=user, course=course)

        factories.ProductFactory(target_courses=(course, ))

        self.assertEqual(models.Notification.objects.count(), 1)
