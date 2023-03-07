"""
Test suite for notification models
"""
import datetime
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import factories
from joanie.core.exceptions import GradeError
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend



class NotificationModelsTestCase(TestCase):
    """Test suite for the Notification model."""

    def test_models_notification_str_not_sent(self):
        user = factories.UserFactory(username="AmeliaP")
        course = factories.CourseFactory(title="time-travel class")
        course_wish = factories.CourseWishFactory.create(owner=user, course=course)

        course_run = factories.CourseRunFactory(course=course, is_listed=True, title="session 42")

        notification = factories.NotificationFactory(
            owner=user,
            notif_subject=course_wish,
            notif_object=course_run
        )
        print(notification)
        self.assertEqual(
            str(notification),
            "'AmeliaP' hasn't been notified about 'session 42 [starting on]' according to "
            "'AmeliaP's wish to participate at the course time-travel class' yet",
        )

    def test_models_notification_str_sent(self):
        user = factories.UserFactory(username="AmeliaP")
        course = factories.CourseFactory(title="time-travel class")
        course_wish = factories.CourseWishFactory.create(owner=user, course=course)

        course_run = factories.CourseRunFactory(course=course, is_listed=True, title="session 42")

        notified_at = datetime.datetime(2010, 1, 1)

        notification = factories.NotificationFactory(
            owner=user,
            notif_subject=course_wish,
            notif_object=course_run,
            notified_at=notified_at
        )
        print(notification)
        self.assertEqual(
            str(notification),
            "'AmeliaP' has been notified about 'session 42 [starting on]' according to "
            "'AmeliaP's wish to participate at the course time-travel class' "
            "at '2010-01-01 00:00:00'",
        )
