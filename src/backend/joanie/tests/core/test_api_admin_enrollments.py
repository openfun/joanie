"""Test suite for the admin enrollments API endpoints."""

import uuid
from http import HTTPStatus
from unittest import mock

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

    def test_api_admin_enrollments_filter_by_query(self):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        a query. This query should allow to search enrollment on course_run title,
        resource_link and course code.
        """
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # - Create random enrollments
        factories.EnrollmentFactory.create_batch(2)

        # - Create an enrollment to test the query filter
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            title="Python for beginners",
            resource_link="https://example.com/python-for-beginners",
            course__code="PY101",
        )
        course_run.translations.create(
            language_code="fr-fr", title="Python pour les débutants"
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run)

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 3)

        # Prepare queries to test
        queries = [
            "PY101",
            "101",
            "beginners",
            "débutant",
            "https://example.com/python-for-beginners",
            "python-for-beginners",
        ]

        for query in queries:
            response = self.client.get(f"/api/v1.0/admin/enrollments/?query={query}")
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(enrollment.id))

    def test_api_admin_enrollments_filter_by_course_run_ids(self):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        course run ids.
        """

        enrollments = factories.EnrollmentFactory.create_batch(3)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 3)

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/?course_run_ids={enrollments[0].course_run.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(enrollments[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/"
            f"?course_run_ids={enrollments[0].course_run.id}"
            f"&course_run_ids={enrollments[2].course_run.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(enrollments[2].id))
        self.assertEqual(content["results"][1]["id"], str(enrollments[0].id))

    def test_api_admin_enrollments_filter_by_user_ids(self):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        user ids.
        """

        enrollments = factories.EnrollmentFactory.create_batch(3)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 3)

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/?user_ids={enrollments[0].user.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(enrollments[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/"
            f"?user_ids={enrollments[0].user.id}"
            f"&user_ids={enrollments[2].user.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(enrollments[2].id))
        self.assertEqual(content["results"][1]["id"], str(enrollments[0].id))

    def test_api_admin_enrollments_filter_by_ids(self):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        their ids.
        """

        enrollments = factories.EnrollmentFactory.create_batch(3)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 3)

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/?ids={enrollments[0].id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(enrollments[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/enrollments/"
            f"?ids={enrollments[0].id}"
            f"&ids={enrollments[2].id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(enrollments[2].id))
        self.assertEqual(content["results"][1]["id"], str(enrollments[0].id))

    def test_api_admin_enrollments_filter_by_is_active(self):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        their active state.
        """

        inactive_enrollment = factories.EnrollmentFactory.create(is_active=False)
        active_enrollment = factories.EnrollmentFactory.create(is_active=True)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)

        response = self.client.get("/api/v1.0/admin/enrollments/?is_active=false")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(inactive_enrollment.id))

        response = self.client.get("/api/v1.0/admin/enrollments/?is_active=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(active_enrollment.id))

    @mock.patch("joanie.core.models.courses.Enrollment.set")
    def test_api_admin_enrollments_filter_by_state(self, _):
        """
        Authenticated admin user should be able to filter all existing enrollments by
        their state.
        """

        set_enrollment = factories.EnrollmentFactory.create(
            state=enums.ENROLLMENT_STATE_SET
        )
        failed_enrollment = factories.EnrollmentFactory.create(
            state=enums.ENROLLMENT_STATE_FAILED
        )

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/enrollments/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)

        response = self.client.get("/api/v1.0/admin/enrollments/?state=set")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(set_enrollment.id))

        response = self.client.get("/api/v1.0/admin/enrollments/?state=failed")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(failed_enrollment.id))

    def test_api_admin_enrollments_create(self):
        """Create an enrollment should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/enrollments/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_enrollments_update(self):
        """
        Update an enrollment should be allowed but only is_active should be writable.
        """

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN, is_listed=True
        )
        enrollment = factories.EnrollmentFactory(
            user=user, course_run=course_run, is_active=True, was_created_by_order=False
        )

        enrollment_id = enrollment.id
        enrollment_created_on = enrollment.created_on
        enrollment_state = enrollment.state

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={
                "id": uuid.uuid4(),
                "is_active": False,
                "was_created_by_order": True,
                "user": uuid.uuid4(),
                "course_run": uuid.uuid4(),
                "certificate": uuid.uuid4(),
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
                "state": None,
            },
        )

        # We have to refresh enrollment as updated_on should have been updated
        enrollment.refresh_from_db()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(enrollment_id),
                "created_on": format_date(enrollment_created_on),
                "updated_on": format_date(enrollment.updated_on),
                "state": enrollment_state,
                "is_active": False,
                "was_created_by_order": False,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.get_full_name(),
                    "email": user.email,
                },
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "is_gradable": course_run.is_gradable,
                    "is_listed": course_run.is_listed,
                    "languages": course_run.languages,
                    "start": format_date(course_run.start),
                    "end": format_date(course_run.end),
                    "enrollment_start": format_date(course_run.enrollment_start),
                    "enrollment_end": format_date(course_run.enrollment_end),
                    "uri": course_run.uri,
                    "state": {
                        "call_to_action": course_run.state.get("call_to_action"),
                        "datetime": format_date(course_run.state.get("datetime")),
                        "priority": course_run.state.get("priority"),
                        "text": course_run.state.get("text"),
                    },
                },
                "certificate": None,
            },
        )

    def test_api_admin_enrollments_partial_update(self):
        """
        Update partially an enrollment should be allowed
        for the field `is_active` exclusively.
        """
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory(is_active=True)

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"is_active": False},
        )

        enrollment.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(enrollment.id),
                "created_on": format_date(enrollment.created_on),
                "updated_on": format_date(enrollment.updated_on),
                "state": enrollment.state,
                "is_active": False,
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
                "certificate": None,
            },
        )

    def test_api_admin_enrollments_delete(self):
        """An admin user should not be able to delete an enrollment."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory()

        response = self.client.delete(f"/api/v1.0/admin/enrollments/{enrollment.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
