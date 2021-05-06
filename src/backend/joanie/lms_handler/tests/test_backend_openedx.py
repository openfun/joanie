"""Test suite for the OpenEdX LMS Backend."""
import json
import random

from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.core.exceptions import EnrollmentError
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://openedx.test",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r".*",
        }
    ]
)
class OpenEdXLMSBackendTestCase(TestCase):
    """Test suite for the OpenEdX LMS Backend."""

    def test_backend_openedx_extract_course_id_from_resource_link(self):
        """
        From a resource_link, OpenEdX backend should be able
        to extract a course_id
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        course_id = backend.extract_course_id(resource_link)
        self.assertEqual(course_id, "course-v1:edx+000001+Demo_Course")

    @responses.activate
    def test_backend_openedx_get_enrollment_to_a_course_which_user_is_enrolled(self):
        """
        Retrieving course run's enrollment which the provided user is enrolled
        should return enrollment details.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = (
            "http://openedx.test/api/enrollment/v1/enrollment/"
            f"{username},course-v1:edx+000001+Demo_Course"
        )
        expected_json_response = {"is_active": True}

        responses.add(
            responses.GET,
            url,
            status=200,
            json=expected_json_response,
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertIsNone(responses.calls[0].request.body)
        self.assertEqual(enrollment, expected_json_response)

    @responses.activate
    def test_backend_openedx_get_enrollment_failed(self):
        """
        If retrieving course run's enrollment failed, it should return None.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = (
            "http://openedx.test/api/enrollment/v1/enrollment/"
            f"{username},course-v1:edx+000001+Demo_Course"
        )

        responses.add(
            responses.GET, url, status=500, json={"error": "Something went wrong..."}
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertIsNone(responses.calls[0].request.body)
        self.assertIsNone(enrollment)

    @responses.activate
    def test_backend_openedx_set_enrollment_successfully(self):
        """
        Updating a user's enrollment to a course run should return a boolean
        corresponding to the success of the operation.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        requested_state = random.choice([True, False])
        expected_json_response = {"is_active": requested_state}

        responses.add(
            responses.POST,
            url,
            status=200,
            json=expected_json_response,
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        backend.set_enrollment(username, resource_link, requested_state)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": requested_state,
                "user": username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_wrong_state(self):
        """
        When updating a user's enrollment, the LMS may return a 200 but not
        with the enrollment status we requested. We should not fall for this.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        requested_state = random.choice([True, False])

        # Let the LMS return the wrong state
        lms_state = not requested_state
        expected_json_response = {"is_active": lms_state}

        responses.add(
            responses.POST,
            url,
            status=200,
            json=expected_json_response,
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        with self.assertRaises(EnrollmentError):
            backend.set_enrollment(username, resource_link, requested_state)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": requested_state,
                "user": username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_failed(self):
        """
        In the case where update a user's enrollment to a course run failed,
        it should raise an EnrollmentError.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        enrollment_state = random.choice([True, False])

        responses.add(
            responses.POST,
            url,
            status=500,
            json={"is_active": enrollment_state},
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        course_id = backend.extract_course_id(resource_link)

        with self.assertRaises(EnrollmentError):
            backend.set_enrollment(username, resource_link, enrollment_state)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": enrollment_state,
                "user": username,
                "course_details": {"course_id": course_id},
            },
        )
