"""
Test suite for Course run Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories


class CourseRunAdminApiTest(TestCase):
    """
    Test suite for Course run Admin API.
    """

    def test_admin_api_course_runs_request_without_authentication(self):
        """
        Anonymous users should not be able to request course runs endpoint.
        """
        response = self.client.get("/api/v1.0/admin/course-runs/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_course_runs_request_with_lambda_user(self):
        """
        Lambda user should not be able to request course runs endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/course-runs/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_course_runs_list(self):
        """
        Staff user should be able to get a paginated list of course runs.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_runs_count = random.randint(1, 10)
        factories.CourseRunFactory.create_batch(course_runs_count)

        response = self.client.get("/api/v1.0/admin/course-runs/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], course_runs_count)

    def test_admin_api_course_runs_list_filter_by_query(self):
        """
        Staff user should be able to get a paginated list of course runs filtered through
        a search text
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_runs_count = random.randint(1, 10)
        items = factories.CourseRunFactory.create_batch(course_runs_count)

        response = self.client.get("/api/v1.0/admin/course-runs/?query=")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], course_runs_count)

        response = self.client.get(
            f"/api/v1.0/admin/course-runs/?query={items[0].title}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)

    def test_admin_api_course_runs_list_filter_by_query_language(self):
        """
        Staff user should be able to get a paginated list of course runs filtered through
        a search text and with different languages
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        item = factories.CourseRunFactory(title="Course run 1")
        item.translations.create(language_code="fr-fr", title="Session 1")

        response = self.client.get("/api/v1.0/admin/course-runs/?query=Course")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Course run 1")

        response = self.client.get(
            "/api/v1.0/admin/course-runs/?query=Session", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Session 1")

        response = self.client.get(
            "/api/v1.0/admin/course-runs/?query=Course", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Session 1")

    def test_admin_api_course_runs_get(self):
        """
        Staff user should be able to get a course run through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory()

        response = self.client.get(f"/api/v1.0/admin/course-runs/{course_run.id}/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course_run.id))
        self.assertEqual(
            content["start"], course_run.start.isoformat().replace("+00:00", "Z")
        )
        self.assertEqual(
            content["end"], course_run.end.isoformat().replace("+00:00", "Z")
        )
        self.assertEqual(
            content["enrollment_start"],
            course_run.enrollment_start.isoformat().replace("+00:00", "Z"),
        )
        self.assertEqual(
            content["enrollment_end"],
            course_run.enrollment_end.isoformat().replace("+00:00", "Z"),
        )

    def test_admin_api_course_runs_create(self):
        """
        Staff user should be able to create a course run.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        data = {
            "title": "Run 001",
            "languages": ["fr"],
            "resource_link": "https://my-lms.org/course-001/run-001",
            "course": str(course.id),
            "enrollment_start": "2023-01-01T00:00:00Z",
            "enrollment_end": "2023-01-02T00:00:00Z",
            "start": "2023-01-03T00:00:00Z",
            "end": "2023-01-04T00:00:00Z",
        }

        response = self.client.post(
            "/api/v1.0/admin/course-runs/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(
            content["resource_link"], "https://my-lms.org/course-001/run-001"
        )
        self.assertEqual(content["enrollment_start"], "2023-01-01T00:00:00Z")
        self.assertEqual(content["enrollment_end"], "2023-01-02T00:00:00Z")
        self.assertEqual(content["start"], "2023-01-03T00:00:00Z")
        self.assertEqual(content["end"], "2023-01-04T00:00:00Z")

    def test_admin_api_course_runs_update(self):
        """
        Staff user should be able to update a course_run.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(
            title="Run 001",
            languages=["fr"],
            resource_link="https://my-lms.org/course-001/run-001",
        )
        payload = {
            "title": "Updated Run 001",
            "languages": ["en"],
            "resource_link": "https://my-lms.org/course-001/updated-run-001",
            "course": str(course_run.course.id),
        }

        response = self.client.put(
            f"/api/v1.0/admin/course-runs/{course_run.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course_run.id))
        self.assertEqual(content["title"], "Updated Run 001")
        self.assertListEqual(content["languages"], ["en"])
        self.assertEqual(
            content["resource_link"], "https://my-lms.org/course-001/updated-run-001"
        )

    def test_admin_api_course_runs_partially_update(self):
        """
        Staff user should be able to partially update a course run.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(title="Course Run 001")

        response = self.client.patch(
            f"/api/v1.0/admin/course-runs/{course_run.id}/",
            content_type="application/json",
            data={"title": "Updated Run 001"},
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course_run.id))
        self.assertEqual(content["title"], "Updated Run 001")

    def test_admin_api_course_runs_delete(self):
        """
        Staff user should be able to delete a course run.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory()

        response = self.client.delete(f"/api/v1.0/admin/course-runs/{course_run.id}/")

        self.assertEqual(response.status_code, 204)
