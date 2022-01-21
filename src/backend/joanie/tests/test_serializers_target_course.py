"""Test suite for the TargetCourseSerializer"""
from collections import OrderedDict

from django.test import TestCase

from joanie.core.factories import CourseFactory
from joanie.core.serializers import (
    CourseRunSerializer,
    OrganizationSerializer,
    TargetCourseSerializer,
)


class TargetCourseSerializerTestCase(TestCase):
    """TargetCourseSerializer test case"""

    def test_serializer_target_course_is_read_only(self):
        """A target course should be read only."""
        course = CourseFactory.build()
        course_runs = CourseRunSerializer().to_representation(course.course_runs)
        organization = OrganizationSerializer().to_representation(course.organization)

        data = {
            "code": str(course.code),
            "course_runs": course_runs,
            "is_graded": False,
            "organization": organization,
            "position": 9999,
            "title": course.title,
        }
        serializer = TargetCourseSerializer(data=data)

        # - Serializer should be valid
        self.assertTrue(serializer.is_valid())
        # - but validated data should be an empty ordered dict
        self.assertEqual(serializer.validated_data, OrderedDict([]))
