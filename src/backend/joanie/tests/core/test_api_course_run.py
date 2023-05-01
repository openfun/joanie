"""Test suite for the CourseRun API"""
from unittest import mock

from joanie.core import factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseRunApiTest(BaseAPITestCase):
    """Test the API of the CourseRun resource."""

    def test_api_course_run_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of course runs
        for anonymous users.
        """
        factories.CourseRunFactory()

        response = self.client.get("/api/v1.0/course-runs/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_run_read_list_authenticated(self):
        """
        It should not be possible to retrieve the list of course runs
        for authenticated users.
        """
        factories.CourseRunFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/course-runs/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_run_read_detail(self, _):
        """
        Any users should be allowed to retrieve a listed course run with minimal db access.
        """
        course_run = factories.CourseRunFactory(is_listed=True)

        with self.assertNumQueries(1):
            response = self.client.get(f"/api/v1.0/course-runs/{course_run.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(course_run.id),
                "resource_link": course_run.resource_link,
                "course": {
                    "id": str(course_run.course.id),
                    "code": str(course_run.course.code),
                    "title": str(course_run.course.title),
                    "cover": "_this_field_is_mocked",
                },
                "title": course_run.title,
                "state": {
                    "priority": course_run.state["priority"],
                    "datetime": course_run.state["datetime"]
                    .isoformat()
                    .replace("+00:00", "Z")
                    if course_run.state["datetime"]
                    else None,
                    "call_to_action": course_run.state["call_to_action"],
                    "text": course_run.state["text"],
                },
                "enrollment_start": course_run.enrollment_start.isoformat().replace(
                    "+00:00", "Z"
                ),
                "enrollment_end": course_run.enrollment_end.isoformat().replace(
                    "+00:00", "Z"
                ),
                "start": course_run.start.isoformat().replace("+00:00", "Z"),
                "end": course_run.end.isoformat().replace("+00:00", "Z"),
            },
        )

    def test_api_course_run_read_detail_not_listed_anonymous(self):
        """
        An anonymous user should not be allowed to retrieve a course run not listed.
        """
        course_run = factories.CourseRunFactory(is_listed=False)

        response = self.client.get(f"/api/v1.0/course-runs/{course_run.id}/")

        self.assertContains(
            response,
            "Not found.",
            status_code=404,
        )

    def test_api_course_run_read_detail_not_listed_authenticated(self):
        """
        An authenticated user should not be allowed to retrieve a course run not listed.
        """
        course_run = factories.CourseRunFactory(is_listed=False)
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/course-runs/{course_run.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Not found.",
            status_code=404,
        )

    def test_api_course_run_create_anonymous(self):
        """Anonymous users should not be allowed to create a course run."""
        course = factories.CourseFactory()
        data = {
            "resource_link": "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "course": course.id,
        }

        response = self.client.post("/api/v1.0/course-runs/", data=data)

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.CourseRun.objects.count(), 0)

    def test_api_course_run_create_authenticated(self):
        """Authenticated users should not be allowed to create a course run."""
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        data = {
            "resource_link": "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
            "course": course.id,
        }

        response = self.client.post(
            "/api/v1.0/course-runs/", data=data, HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.CourseRun.objects.count(), 0)

    def test_api_course_run_update_anonymous(self):
        """Anonymous users should not be allowed to update a course run."""
        course_run = factories.CourseRunFactory(
            resource_link="https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        )
        course = factories.CourseFactory()

        data = {
            "resource_link": "https://perdu.com",
            "course": course.id,
            "languages": ["en", "fr"],
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
        }

        response = self.client.put(f"/api/v1.0/course-runs/{course_run.id}/", data=data)

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        course_run.refresh_from_db()
        self.assertEqual(
            course_run.resource_link,
            "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
        )

    def test_api_course_run_update_authenticated(self):
        """Authenticated users should not be allowed to update a course run."""
        course_run = factories.CourseRunFactory(
            resource_link="https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        )
        course = factories.CourseFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        data = {
            "resource_link": "https://perdu.com",
            "course": course.id,
            "languages": ["en", "fr"],
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
        }

        response = self.client.put(
            f"/api/v1.0/course-runs/{course_run.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        course_run.refresh_from_db()
        self.assertEqual(
            course_run.resource_link,
            "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
        )

    def test_api_course_run_partial_update_anonymous(self):
        """Anonymous users should not be allowed to partially update a course run."""
        course_run = factories.CourseRunFactory(
            resource_link="https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        )

        data = {
            "resource_link": "https://perdu.com",
        }

        response = self.client.patch(
            f"/api/v1.0/course-runs/{course_run.id}/", data=data
        )

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        course_run.refresh_from_db()
        self.assertEqual(
            course_run.resource_link,
            "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
        )

    def test_api_course_run_partial_update_authenticated(self):
        """Authenticated users should not be allowed to partially update a course run."""
        course_run = factories.CourseRunFactory(
            resource_link="https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/"
        )
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        data = {
            "resource_link": "https://perdu.com",
        }

        response = self.client.patch(
            f"/api/v1.0/course-runs/{course_run.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        course_run.refresh_from_db()
        self.assertEqual(
            course_run.resource_link,
            "https://example.edx:8073/courses/course-v1:edX+DemoX+01/course/",
        )

    def test_api_course_run_delete_anonymous(self):
        """Anonymous users should not be allowed to delete a course run."""
        course_run = factories.CourseRunFactory()

        response = self.client.delete(f"/api/v1.0/course-runs/{course_run.id}/")

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.CourseRun.objects.count(), 1)

    def test_api_course_run_delete_authenticated(self):
        """Authenticated users should not be allowed to delete a course run."""
        course_run = factories.CourseRunFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/course-runs/{course_run.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.CourseRun.objects.count(), 1)
