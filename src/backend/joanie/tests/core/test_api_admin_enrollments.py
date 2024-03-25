"""Test suite for the admin enrollments API endpoints."""

import uuid
from http import HTTPStatus

from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import CourseState
from joanie.tests import format_date


class OrdersAdminApiTestCase(TestCase):
    """Test suite for the admin enrollments API endpoints."""

    maxDiff = None

    def test_api_admin_enrollments_request_without_authentication(self):
        """
        Anonymous users should not be able to request enrollments endpoint.
        """
        response = self.client.get("/api/v1.0/admin/enrollments/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_enrollments_request_with_lambda_user(self):
        """
        Lambda user should not be able to request enrollments endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_enrollments_list(self):
        """Authenticated admin user should be able to list all existing enrollments."""
        # Create two enrollments
        enrollments = factories.EnrollmentFactory.create_batch(2)

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        with self.assertNumQueries(4):
            response = self.client.get("/api/v1.0/admin/enrollments/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "course_run": {
                        "id": str(enrollment.course_run.id),
                        "resource_link": enrollment.course_run.resource_link,
                        "title": enrollment.course_run.title,
                        "is_gradable": enrollment.course_run.is_gradable,
                        "is_listed": enrollment.course_run.is_listed,
                        "languages": enrollment.course_run.languages,
                        "start": format_date(enrollment.course_run.start),
                        "end": format_date(enrollment.course_run.end),
                        "enrollment_start": format_date(
                            enrollment.course_run.enrollment_start
                        ),
                        "enrollment_end": format_date(
                            enrollment.course_run.enrollment_end
                        ),
                        "uri": enrollment.course_run.uri,
                        "state": {
                            "call_to_action": enrollment.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": format_date(
                                enrollment.course_run.state.get("datetime")
                            ),
                            "priority": enrollment.course_run.state.get("priority"),
                            "text": enrollment.course_run.state.get("text"),
                        },
                    },
                    "user_name": enrollment.user.username,
                    "id": str(enrollment.id),
                    "state": enrollment.state,
                    "is_active": enrollment.is_active,
                }
                for enrollment in sorted(
                    enrollments, key=lambda x: x.created_on, reverse=True
                )
            ],
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_enrollments_retrieve(self):
        """
        An admin user should be able to retrieve a single enrollment through its id.
        """

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create an enrollment with a related certificate
        enrollment = factories.EnrollmentFactory()

        # Create certificate
        factories.EnrollmentCertificateFactory(enrollment=enrollment)

        with self.assertNumQueries(4):
            response = self.client.get(f"/api/v1.0/admin/enrollments/{enrollment.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "created_on": format_date(enrollment.created_on),
                "updated_on": format_date(enrollment.updated_on),
                "state": enrollment.state,
                "is_active": enrollment.is_active,
                "was_created_by_order": enrollment.was_created_by_order,
                "user": {
                    "id": str(enrollment.user.id),
                    "username": enrollment.user.username,
                    "full_name": enrollment.user.get_full_name(),
                    "email": enrollment.user.email,
                },
                "course_run": {
                    "id": str(enrollment.course_run.id),
                    "resource_link": enrollment.course_run.resource_link,
                    "title": enrollment.course_run.title,
                    "is_gradable": enrollment.course_run.is_gradable,
                    "is_listed": enrollment.course_run.is_listed,
                    "languages": enrollment.course_run.languages,
                    "start": format_date(enrollment.course_run.start),
                    "end": format_date(enrollment.course_run.end),
                    "enrollment_start": format_date(
                        enrollment.course_run.enrollment_start
                    ),
                    "enrollment_end": format_date(enrollment.course_run.enrollment_end),
                    "uri": enrollment.course_run.uri,
                    "state": {
                        "call_to_action": enrollment.course_run.state.get(
                            "call_to_action"
                        ),
                        "datetime": format_date(
                            enrollment.course_run.state.get("datetime")
                        ),
                        "priority": enrollment.course_run.state.get("priority"),
                        "text": enrollment.course_run.state.get("text"),
                    },
                },
                "certificate": {
                    "id": str(enrollment.certificate.id),
                    "definition_title": enrollment.certificate.certificate_definition.title,
                    "issued_on": format_date(enrollment.certificate.issued_on),
                },
            },
        )

    def test_api_admin_enrollments_create(self):
        """Create an enrollment should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/enrollments/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_enrollments_delete(self):
        """An admin user should not be able to delete an enrollment."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory()

        response = self.client.delete(f"/api/v1.0/admin/enrollments/{enrollment.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
