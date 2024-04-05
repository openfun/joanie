"""Test suite for remote API endpoints on course run in the edx_imports application."""

from http import HTTPStatus

from django.test import TestCase
from django.test.utils import override_settings

from joanie.core import factories
from joanie.tests import format_date


class EdxImportsCourseRunApiTest(TestCase):
    """Test suite for remote API endpoints on course run in the edx_imports application."""

    maxDiff = None

    def test_course_run_api_without_api_token(self):
        """Test course run API without API token should return 403."""
        response = self.client.get("/api/v1.0/edx_imports/course-run/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_course_run_api_with_invalid_api_token(self):
        """Test course run API with invalid API token should return 403."""
        response = self.client.get(
            "/api/v1.0/edx_imports/course-run/",
            HTTP_AUTHORIZATION="Bearer invalid_secret_token_sample",
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_course_run_api_with_valid_api_token_but_no_resource_link_parameter(self):
        """
        Test course run API with valid API token but no resource_link parameter should return 400.
        """
        response = self.client.get(
            "/api/v1.0/edx_imports/course-run/",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"detail": "Query parameter `resource_link` is required."}
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_course_run_api_valid_api_token_unknown_resource_link(self):
        """Test course run API with valid API token and unknown resource_link should return 404."""
        response = self.client.get(
            "/api/v1.0/edx_imports/course-run/?resource_link=unknown_resource_link",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            response.json(), {"detail": "No CourseRun matches the given query."}
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_course_run_api_valid_api_token_known_resource_link(self):
        """Test course run API with valid API token and known resource_link should return 200."""
        course = factories.CourseFactory.create()
        course_run = factories.CourseRunFactory.create(course=course)
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")
        response = self.client.get(
            f"/api/v1.0/edx_imports/course-run/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(course_run.id),
                "start": format_date(course_run.start),
                "end": format_date(course_run.end),
                "enrollment_start": format_date(course_run.enrollment_start),
                "enrollment_end": format_date(course_run.enrollment_end),
                "course": {
                    "code": course_run.course.code,
                    "title": course_run.course.title,
                    "id": str(course_run.course.id),
                    "state": {
                        "priority": course_run.course.state["priority"],
                        "datetime": format_date(course_run.course.state["datetime"]),
                        "call_to_action": course_run.course.state["call_to_action"],
                        "text": course_run.course.state["text"],
                    },
                },
                "resource_link": course_run.resource_link,
                "title": course_run.title,
                "is_gradable": course_run.is_gradable,
                "is_listed": course_run.is_listed,
                "languages": course_run.languages,
                "uri": course_run.uri,
                "state": {
                    "priority": course_run.state["priority"],
                    "datetime": format_date(course_run.state["datetime"]),
                    "call_to_action": course_run.state["call_to_action"],
                    "text": course_run.state["text"],
                },
            },
        )
