"""Test suite for the admin enrollments API endpoints."""

import random
import uuid
from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import CourseState, Enrollment
from joanie.tests import format_date


# pylint: disable=too-many-public-methods, too-many-lines
class OrdersAdminApiTestCase(TestCase):
    """Test suite for the admin enrollments API endpoints."""

    maxDiff = None

    def create_closed_course_run(self, count=1, **kwargs):
        """Create course runs closed for enrollment."""
        closed_states = [
            CourseState.FUTURE_NOT_YET_OPEN,
            CourseState.FUTURE_CLOSED,
            CourseState.ONGOING_CLOSED,
            CourseState.ARCHIVED_CLOSED,
        ]
        if count > 1:
            return factories.CourseRunFactory.create_batch(
                count,
                state=random.choice(closed_states),
                **kwargs,
            )

        return factories.CourseRunFactory(
            state=random.choice(closed_states),
            **kwargs,
        )

    def create_opened_course_run(self, count=1, **kwargs):
        """Create course runs opened for enrollment."""
        open_states = [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
        ]
        if count > 1:
            return factories.CourseRunFactory.create_batch(
                count,
                state=random.choice(open_states),
                **kwargs,
            )

        return factories.CourseRunFactory(
            state=random.choice(open_states),
            **kwargs,
        )

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
                    "user_name": enrollment.user.get_full_name(),
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

    def test_api_admin_enrollments_create_for_closed_course_run(self):
        """
        Admin user can create an enrollment even if the course run is closed and for
        an existing user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run = self.create_closed_course_run(
            is_listed=True,
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        data = {
            "user": user.id,
            "course_run": course_run.id,
            "is_active": True,
            "was_created_by_order": False,
        }

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_api_admin_enrollments_create_for_opened_course_run(self):
        """
        Admin user can create an enrollment when the course run is opened and for an existing user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        course_run = self.create_opened_course_run(is_listed=True)

        data = {
            "user": user.id,
            "course_run": course_run.id,
            "is_active": True,
            "was_created_by_order": False,
        }

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_api_admin_enrollments_create_with_missing_user_id_should_fail(self):
        """
        Admin user cannot create an enrollment for a user if it's missing the user id in the
        payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_opened_course_run(is_listed=True)

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            content_type="application/json",
            data={"course_run": course_run.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": ["You must provide a user_id to create/update an enrollment."]},
        )
        self.assertFalse(Enrollment.objects.exists())

    def test_api_admin_enrollments_create_with_missing_course_id_should_fail(self):
        """
        Admin user cannot create an enrollment for a user if it's missing the course id in the
        payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            content_type="application/json",
            data={"user": user.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    "You must provide a course_run_id to create/update an enrollment."
                ]
            },
        )
        self.assertFalse(Enrollment.objects.exists())

    def test_api_admin_enrollments_create_with_unexisting_course_id_should_fail(self):
        """
        Admin user cannot create an enrollment for a user if it passes a course id that
        does not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        fake_course_run_id = uuid.uuid4()

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            content_type="application/json",
            data={"user": user.id, "course_run": fake_course_run_id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'A course run with id "{fake_course_run_id}" does not exist.'
                ]
            },
        )
        self.assertFalse(Enrollment.objects.exists())

    def test_api_admin_enrollments_create_with_unexsting_user_id_should_fail(self):
        """
        Admin user cannot create an enrollment for a user if it passes a user id that
        does not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_opened_course_run(is_listed=True)
        fake_user_id = uuid.uuid4()

        response = self.client.post(
            "/api/v1.0/admin/enrollments/",
            content_type="application/json",
            data={"user": fake_user_id, "course_run": course_run.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": [f'A user with the id "{fake_user_id}" does not exist.']},
        )
        self.assertFalse(Enrollment.objects.exists())

    def test_api_admin_enrollments_update_missing_course_id_should_fail(self):
        """
        Admin user should not be able to update an enrollment if the course run id is missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            user=user, is_active=True, was_created_by_order=False
        )

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={
                "id": enrollment.id,
                "certificate": uuid.uuid4(),
                "user": user.id,
                "is_active": True,
                "was_created_by_order": True,
                "state": None,
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    "You must provide a course_run_id to create/update an enrollment."
                ]
            },
        )

    def test_api_admin_enrollments_update_missing_user_id_should_fail(self):
        """
        Admin user should not be able to update an enrollment if the user id is missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_closed_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, is_active=True, was_created_by_order=False
        )

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={
                "id": enrollment.id,
                "certificate": uuid.uuid4(),
                "course_run": course_run.id,
                "is_active": False,
                "was_created_by_order": True,
                "state": None,
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": ["You must provide a user_id to create/update an enrollment."]},
        )

    def test_api_admin_enrollments_update_unexisting_course_id_should_fail(self):
        """
        Admin user should not be able to update an enrollment if the course run id is does
        not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            user=user, is_active=True, was_created_by_order=False
        )
        fake_course_run_id = uuid.uuid4()

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={
                "id": enrollment.id,
                "certificate": uuid.uuid4(),
                "user": user.id,
                "course_run": fake_course_run_id,
                "is_active": True,
                "was_created_by_order": True,
                "state": None,
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'A course run with id "{fake_course_run_id}" does not exist.'
                ]
            },
        )

    def test_api_admin_enrollments_update_unexisting_user_id_should_fail(self):
        """
        Admin user should not be able to update an enrollment if the user id is does not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_closed_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, is_active=True, was_created_by_order=False
        )
        fake_user_id = uuid.uuid4()

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={
                "id": enrollment.id,
                "certificate": uuid.uuid4(),
                "user": fake_user_id,
                "course_run": course_run.id,
                "is_active": True,
                "was_created_by_order": True,
                "state": None,
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": [f'A user with the id "{fake_user_id}" does not exist.']},
        )

    def test_api_admin_enrollments_update_when_course_run_is_closed(self):
        """
        Admin user should be able to update an enrollment even if the course run is closed,
        only `is_active` field should be writable.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run = self.create_closed_course_run(
            is_listed=True,
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        enrollment = factories.EnrollmentFactory(
            user=user,
            course_run=course_run,
            is_active=True,
        )
        enrollment_created_on = enrollment.created_on

        response = self.client.put(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            data={
                "id": enrollment.id,
                "certificate": uuid.uuid4(),
                "user": user.id,
                "course_run": course_run.id,
                "is_active": False,
                "was_created_by_order": True,
                "state": None,
                "created_on": format_date(timezone.now()),
                "updated_on": format_date(timezone.now()),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(response.json().get("is_active"))
        self.assertEqual(response.json().get("state"), enums.ENROLLMENT_STATE_SET)
        self.assertEqual(
            response.json().get("created_on"), format_date(enrollment_created_on)
        )

    def test_api_admin_enrollments_update_on_opened_course_run(self):
        """
        An admin can update an enrollment on an opened course run but only `is_active`
        should be writable.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        course_run = self.create_opened_course_run(is_listed=True)
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
                "id": enrollment.id,
                "is_active": False,
                "was_created_by_order": True,
                "user": user.id,
                "course_run": course_run.id,
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
        Admin user can update partially an enrollment for the field `is_active` exclusively.
        """
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        course_run = self.create_opened_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(
            user=user, course_run=course_run, is_active=True, was_created_by_order=False
        )

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"user": user.id, "course_run": course_run.id, "is_active": False},
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

    def test_api_admin_enrollment_partial_update_on_closed_course_run(self):
        """
        Admin user can partially update an enrollment even if the course run is
        closed, only `is_active` field should be writable.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run = self.create_closed_course_run(
            is_listed=True,
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        enrollment = factories.EnrollmentFactory(
            user=user,
            course_run=course_run,
            is_active=False,
            was_created_by_order=False,
        )
        enrollment_created_on = enrollment.created_on
        enrollment_state = enrollment.state

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            data={
                "user": user.id,
                "course_run": course_run.id,
                "is_active": True,
                "state": None,
                "created_on": format_date(timezone.now()),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json().get("is_active"))
        self.assertTrue(response.json().get("state"), enrollment_state)
        self.assertEqual(
            response.json().get("created_on"), format_date(enrollment_created_on)
        )

    def test_api_admin_enrollments_partial_update_enrollment_with_unexisting_user_id(
        self,
    ):
        """
        Admin user should not be able to partially update an enrollment if the user id
        does not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_opened_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, is_active=True, was_created_by_order=False
        )
        fake_user_id = uuid.uuid4()

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"user": fake_user_id, "course_run": course_run.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": [f'A user with the id "{fake_user_id}" does not exist.']},
        )

    def test_api_admin_enrollments_partial_update_enrollment_with_unexisting_course_run_id(
        self,
    ):
        """
        Admin user should not be able to partially update an enrollment if the course run id
        does not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            user=user, is_active=True, was_created_by_order=False
        )
        fake_course_run_id = uuid.uuid4()

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"user": user.id, "course_run": fake_course_run_id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    f'A course run with id "{fake_course_run_id}" does not exist.'
                ]
            },
        )

    def test_api_admin_enrollments_partial_update_enrollment_with_missing_user_id(self):
        """
        Admin user should not be able to partially update an enrollment if the user id
        is missing in the payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course_run = self.create_opened_course_run(is_listed=True)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, is_active=True, was_created_by_order=False
        )

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"course_run": course_run.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"__all__": ["You must provide a user_id to create/update an enrollment."]},
        )

    def test_api_admin_enrollments_partial_update_enrollment_with_missing_course_run_id(
        self,
    ):
        """
        Admin user should not be able to partially update an enrollment if the course run id
        is missing in the payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            user=user, is_active=True, was_created_by_order=False
        )

        response = self.client.patch(
            f"/api/v1.0/admin/enrollments/{enrollment.id}/",
            content_type="application/json",
            data={"user": user.id, "is_active": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    "You must provide a course_run_id to create/update an enrollment."
                ]
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
