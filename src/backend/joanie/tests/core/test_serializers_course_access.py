"""Test suite for the course access serializer"""

import random

from django.test import TestCase

from rest_framework import exceptions

from joanie.core import factories, models, serializers


class CourseAccessSerializerTestCase(TestCase):
    """Course access serializer test case"""

    def test_serializers_course_access_no_request_no_course(self):
        """
        The course access serializer should return a 400 if "course_id" is not passed in context.
        """
        user = factories.UserFactory()

        data = {
            "user_id": str(user.id),
            "role": random.choice(models.CourseAccess.ROLE_CHOICES)[0],
        }
        serializer = serializers.CourseAccessSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "non_field_errors": [
                    "You must set a course ID in context to create a new course access."
                ]
            },
        )

    def test_serializers_course_access_no_request_with_course(self):
        """
        The course access serializer should raise a permission error even if a "course_id"
        is passed if there is no request, so no authorized user.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()

        data = {
            "user_id": str(user.id),
            "role": random.choice(models.CourseAccess.ROLE_CHOICES)[0],
        }
        serializer = serializers.CourseAccessSerializer(
            data=data, context={"course_id": str(course.id)}
        )

        with self.assertRaises(exceptions.PermissionDenied):
            self.assertTrue(serializer.is_valid())
