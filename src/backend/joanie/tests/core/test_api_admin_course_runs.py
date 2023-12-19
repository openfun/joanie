"""
Test suite for Course run Admin API.
"""
import random
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories, models
from joanie.tests import format_date


class CourseRunAdminApiTest(TestCase):
    """
    Test suite for Course run Admin API.
    """

    maxDiff = None

    def test_admin_api_course_runs_request_without_authentication(self):
        """
        Anonymous users should not be able to request course runs endpoint.
        """
        response = self.client.get("/api/v1.0/admin/course-runs/")

        self.assertEqual(response.status_code, 401)
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
            },
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
            "course_id": str(course.id),
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
            "course_id": str(course_run.course.id),
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

    def test_admin_api_course_run_read_list_authenticated_with_nested_course_filter_name(
        self,
    ):
        """
        When filtering by name the query returns only relevant CourseRuns
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory.create()
        course_run = factories.CourseRunFactory(
            course=course, is_listed=True, title="This is a test"
        )
        factories.CourseRunFactory(course=course, is_listed=True, title="CourseRun 0")
        factories.CourseRunFactory(course=course, is_listed=True, title="CourseRun 1")
        factories.CourseRunFactory(course=course, is_listed=True, title="CourseRun 2")

        response = self.client.get(
            f"/api/v1.0/admin/courses/{course.id}/course-runs/?query=is%20a",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(course_run.id))
        response = self.client.get(
            f"/api/v1.0/admin/courses/{course.id}/course-runs/?query=Cour",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)

    def test_admin_api_course_run_read_list_authenticated_with_nested_course_filter_start_date(
        self,
    ):
        """
        When filtering by date the query returns only CourseRuns starting at
        or after the given date
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        now = datetime.now(tz=timezone.utc)
        format_time = "%Y-%m-%dT%H:%M:%S"
        course = factories.CourseFactory.create()
        course_run = factories.CourseRunFactory(
            course=course, is_listed=True, start=now
        )
        factories.CourseRunFactory(
            course=course, is_listed=True, start=now - timedelta(weeks=20)
        )

        response = self.client.get(
            f"/api/v1.0/admin/courses/{course.id}/course-runs/?start={now.strftime(format_time)}",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(course_run.id))

        past_date = now - timedelta(weeks=30)
        response = self.client.get(
            (
                f"/api/v1.0/admin/courses/{course.id}/course-runs/"
                f"?start={past_date.strftime(format_time)}"
            ),
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 2)

        future_date = now + timedelta(weeks=30)
        response = self.client.get(
            (
                f"/api/v1.0/admin/courses/{course.id}/course-runs/"
                f"?start={future_date.strftime(format_time)}"
            ),
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_admin_api_course_run_read_list_authenticated_with_nested_course_filter_state(
        self,
    ):
        """
        When filtering by state, the query returns only CourseRuns matching the given state.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        now = datetime.now(tz=timezone.utc)
        course = factories.CourseFactory.create()
        date_pairs = [
            (now - timedelta(hours=3), now - timedelta(hours=3)),
            (now - timedelta(hours=3), now + timedelta(hours=3)),
            (now + timedelta(hours=3), now + timedelta(hours=3)),
        ]
        for start, end in date_pairs:
            for enrollment_start, enrollment_end in date_pairs:
                factories.CourseRunFactory(
                    course=course,
                    start=start,
                    end=end,
                    enrollment_start=enrollment_start,
                    enrollment_end=enrollment_end,
                )
        factories.CourseRunFactory.create_batch(20, course=course)
        all_course_runs = models.CourseRun.objects.all()
        sorted_course_runs = [[] for _ in range(len(models.CourseState.STATE_TEXTS))]

        for course_run in all_course_runs:
            sorted_course_runs[course_run.state["priority"]].append(course_run)

        for state_id in models.CourseState.STATE_TEXTS:
            response = self.client.get(
                (
                    f"/api/v1.0/admin/courses/{course.id}/course-runs/"
                    f"?state={state_id}"
                ),
            )
            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertEqual(content["count"], len(sorted_course_runs[state_id]))
            for course_run in sorted_course_runs[state_id]:
                self.assertTrue(str(course_run.id) in str(content))

        # Non existing state
        response = self.client.get(
            f"/api/v1.0/admin/courses/{course.id}/course-runs/?state=-1",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 0)
