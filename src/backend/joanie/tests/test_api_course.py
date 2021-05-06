"""Tests for the Course API."""
import json

from joanie.core import factories, models

from .base import BaseAPITestCase


class CourseApiTest(BaseAPITestCase):
    """Test the API of the Course object."""

    def test_api_course_read_list_anonymous(self):
        """It should not be possible to retrieve the list of courses for anonymous users."""
        factories.CourseFactory()

        response = self.client.get(
            "/api/courses/",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_read_list_authenticated(self):
        """It should not be possible to retrieve the list of courses for authenticated users."""
        factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.get(
            "/api/courses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_read_detail_anonymous(self):
        """Anonymous users should be allowed to retrieve a course."""
        products = factories.ProductFactory.create_batch(2)
        course = factories.CourseFactory(products=products)

        response = self.client.get("/api/courses/{!s}/".format(course.code))
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "code": course.code,
                "organization": course.organization.code,
                "title": course.title,
                "products": [str(p.uid) for p in products],
            },
        )

    def test_api_course_read_detail_authenticated(self):
        """Authenticated users should be allowed to retrieve a course."""
        products = factories.ProductFactory.create_batch(2)
        course = factories.CourseFactory(products=products)
        token = self.get_user_token("panoramix")

        response = self.client.get(
            "/api/courses/{!s}/".format(course.code),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {
                "code": course.code,
                "organization": course.organization.code,
                "title": course.title,
                "products": [str(p.uid) for p in products],
            },
        )

    def test_api_course_create_anonymous(self):
        """Anonymous users should not be able to create a course."""
        organization = factories.OrganizationFactory()
        products = factories.ProductFactory.create_batch(2)
        data = {
            "code": "123",
            "organization": organization.code,
            "title": "mathématiques",
            "products": [p.id for p in products],
        }
        response = self.client.post("/api/courses/", data=data)

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_create_authenticated(self):
        """Lambda authenticated users should not be able to create a course."""
        organization = factories.OrganizationFactory()
        products = factories.ProductFactory.create_batch(2)
        data = {
            "code": "123",
            "organization": organization.code,
            "title": "mathématiques",
            "products": [p.id for p in products],
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/courses/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_delete_anonymous(self):
        """Anonymous users should not be able to delete a course."""
        course = factories.CourseFactory()

        response = self.client.delete("/api/courses/{!s}/".format(course.id))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated(self):
        """Authenticated users should not be able to delete a course."""
        course = factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.delete(
            "/api/courses/{!s}/".format(course.id),
            HTTP_AUTHORIZATION="Bearer {!s}".format(token),
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_update_detail_anonymous(self):
        """Anonymous users should not be allowed to update a course."""
        course = factories.CourseFactory(code="initial_code")

        response = self.client.get(
            "/api/courses/{!s}/".format(course.code),
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            "/api/courses/{!s}/".format(course.code),
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            "/api/courses/{!s}/".format(course.code),
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

        # Check that nothing was modified
        self.assertEqual(models.Course.objects.count(), 1)
        self.assertTrue(models.Course.objects.filter(code="initial_code").exists())

    def test_api_course_update_detail_authenticated(self):
        """Authenticated users should be allowed to retrieve a course."""
        course = factories.CourseFactory(code="initial_code")
        token = self.get_user_token("panoramix")

        response = self.client.get(
            "/api/courses/{!s}/".format(course.code),
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            "/api/courses/{!s}/".format(course.code),
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            "/api/courses/{!s}/".format(course.code),
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

        # Check that nothing was modified
        self.assertEqual(models.Course.objects.count(), 1)
        self.assertTrue(models.Course.objects.filter(code="initial_code").exists())
