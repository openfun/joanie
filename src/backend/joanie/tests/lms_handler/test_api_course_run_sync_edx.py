"""
Tests for CourseRun web hook.
"""
import json
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from joanie.core.factories import CourseFactory, CourseRunFactory
from joanie.core.models import Course, CourseRun
from joanie.lms_handler import api
from joanie.lms_handler.serializers import SyncCourseRunSerializer


@override_settings(
    JOANIE_SYNC_SECRETS=["shared secret"],
    JOANIE_LMS_BACKENDS=[
        {
            "BASE_URL": "http://localhost:8073",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "JS_BACKEND": "base",
            "JS_COURSE_REGEX": r"^.*/courses/(?<course_id>.*)/course/?$",
        }
    ],
    TIME_ZONE="UTC",
)
class SyncCourseRunApiTestCase(TestCase):
    """Test calls to sync a course run via API endpoint."""

    maxDiff = None

    def test_api_course_run_sync_missing_signature(self):
        """The course run synchronization API endpoint requires a signature."""
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en", "fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync", data, content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Missing authentication."})
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_invalid_signature(self):
        """The course run synchronization API endpoint requires a valid signature."""
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en", "fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=("invalid authorization"),
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Invalid authentication."})
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_missing_resource_link(self):
        """
        If the data submitted is missing a resource link, it should return a 400 error.
        """
        # Data with missing resource link => invalid
        data = {
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en", "fr"],
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"resource_link": ["This field is required."]}
        )
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_invalid_field(self):
        """
        If the submitted data is invalid, the course run synchronization view should return
        a 400 error.
        """
        # Data with invalid start date value
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": 1,
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en", "fr"],
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "start": [
                    (
                        "Datetime has wrong format. Use one of these formats instead: "
                        "YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."
                    )
                ]
            },
        )
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_create_unknown_course_with_title(self):
        """
        If the submitted data is not related to an existing course run and the related course
        can't be found, a new course should be created with the title passed for the course_run.
        """
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
            "title": "my course run",
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course
        course = Course.objects.get()
        self.assertEqual(course.title, "my course run")

        # Check the new course run
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("title")
        self.assertEqual(serializer.data, data)
        course_run.set_current_language("en")
        self.assertEqual(course_run.title, "my course run")

    def test_api_course_run_sync_create_unknown_course_no_title(self):
        """
        If the submitted data does not include the "title" field and is not related to an existing
        course run and the related course can't be found, a new course should be created with the
        course code passed in the course_run synchronization data.
        """
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course
        course = Course.objects.get()
        self.assertEqual(course.title, "DEMOX")

        # Check the new course run
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)
        self.assertEqual(serializer.data, data)

    def test_api_course_run_sync_create(self):
        """
        If the submitted data is not related to an existing course run, a new course run should
        be created.
        """
        CourseFactory(code="DemoX")
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
            "title": "my course run",
        }
        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course run
        course_run = CourseRun.objects.get()
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("title")
        assert serializer.data == data

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_create_partial_required(self):
        """
        If the submitted data is not related to an existing course run and some required fields
        are missing, it should raise a 400.
        """
        CourseFactory(code="DemoX")
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "end": "2021-03-14T09:31:59.417895Z",
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.json(), {"languages": ["This field is required."]})
        self.assertEqual(CourseRun.objects.count(), 0)

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_create_partial_not_required(self):
        """
        If the submitted data is not related to an existing course run and some optional fields
        are missing, it should create the course run.
        """
        CourseFactory(code="DemoX")
        data = {
            "resource_link": "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "created_on": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course run
        course_run = CourseRun.objects.get()
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.update({"start": None, "end": None, "enrollment_start": None})
        self.assertEqual(serializer.data, data)

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_existing_published(self):
        """
        If a course run exists for this resource link, it should be updated.
        """
        link = "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        CourseFactory(code="DemoX")
        CourseRunFactory(resource_link=link)

        data = {
            "resource_link": link,
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
            "title": "my course run",
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the existing course run was updated
        course_run = CourseRun.objects.get()
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("title")
        for field in serializer.fields:
            self.assertEqual(serializer.data[field], data[field], field)
        course_run.set_current_language("en")
        self.assertEqual(course_run.title, "my course run")

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_existing_partial(self):
        """
        If a course run exists for this resource link, it can be partially updated and the other
        fields should not be altered.
        """
        link = "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        course = CourseFactory(code="DemoX")
        course_run = CourseRunFactory(course=course, resource_link=link)

        origin_data = SyncCourseRunSerializer(instance=course_run).data
        data = {
            "resource_link": link,
            "created_on": "2020-11-09T09:31:59.417936Z",
            "end": "2021-03-14T09:31:59.417895Z",
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the course run was updated
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)

        self.assertEqual(serializer.data["created_on"], data["created_on"])
        self.assertEqual(serializer.data["end"], data["end"])
        for field in serializer.fields:
            if field in ("created_on", "end"):
                continue
            self.assertEqual(serializer.data[field], origin_data[field], field)

    @override_settings(
        TIME_ZONE="UTC",
        JOANIE_LMS_BACKENDS=[
            {
                "BASE_URL": "http://localhost:8073",
                "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
                "COURSE_RUN_SYNC_NO_UPDATE_FIELDS": ["languages", "start"],
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
                "JS_BACKEND": "base",
                "JS_COURSE_REGEX": r"^.*/courses/(?<course_id>.*)/course/?$",
            }
        ],
    )
    def test_api_course_run_sync_with_no_update_fields(self):
        """
        If a course run exists and LMS Backend has course run protected fields,
        these fields should not be updated.
        """
        link = "http://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        course = CourseFactory(code="DemoX")
        course_run = CourseRunFactory(course=course, resource_link=link)

        origin_data = SyncCourseRunSerializer(instance=course_run).data
        data = {
            "resource_link": link,
            "created_on": "2020-11-09T09:31:59.417936Z",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["en"],
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/course-runs-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the draft course run was updated except protected fields
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)

        no_update_fields = settings.JOANIE_LMS_BACKENDS[0].get(
            "COURSE_RUN_SYNC_NO_UPDATE_FIELDS"
        )
        serializer_data = json.loads(json.dumps(serializer.data))
        for field in serializer.fields:
            if field in no_update_fields:
                self.assertEqual(serializer_data[field], origin_data[field], field)
            else:
                self.assertEqual(serializer_data[field], data[field], field)
