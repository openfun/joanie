"""
Test suite for Course Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories


class CourseAdminApiTest(TestCase):
    """
    Test suite for Course Admin API.
    """

    def test_admin_api_course_request_without_authentication(self):
        """
        Anonymous users should not be able to request courses endpoint.
        """
        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_course_request_with_lambda_user(self):
        """
        Lambda user should not be able to request courses endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_course_list(self):
        """
        Staff user should be able to get a paginated list of courses.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        courses_count = random.randint(1, 10)
        factories.CourseFactory.create_batch(courses_count)

        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], courses_count)

    def test_admin_api_course_get(self):
        """
        Staff user should be able to get a course through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        response = self.client.get(f"/api/v1.0/admin/courses/{course.id}/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))

    def test_admin_api_course_create(self):
        """
        Staff user should be able to create a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        product = factories.ProductFactory()
        data = {
            "code": "COURSE-001",
            "title": "Course 001",
            "organizations": [str(organization.id)],
            "product_relations": [
                {"product": str(product.id), "organizations": [str(organization.id)]}
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/courses/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, 201)
        content = response.json()

        self.assertIsNotNone(content["code"])
        self.assertEqual(content["code"], "COURSE-001")
        self.assertListEqual(
            content["organizations"],
            [
                {
                    "code": organization.code,
                    "title": organization.title,
                    "id": str(organization.id),
                }
            ],
        )
        self.assertEqual(len(content["product_relations"]), 1)

    def test_admin_api_course_update(self):
        """
        Staff user should be able to update a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory(code="COURSE-001")
        organization = factories.OrganizationFactory()
        payload = {
            "code": "UPDATED-COURSE-001",
            "title": "Updated Course 001",
            "organizations": [str(organization.id)],
        }

        response = self.client.put(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["code"], "UPDATED-COURSE-001")
        self.assertEqual(content["title"], "Updated Course 001")
        self.assertListEqual(
            content["organizations"],
            [
                {
                    "code": organization.code,
                    "title": organization.title,
                    "id": str(organization.id),
                }
            ],
        )

    def test_admin_api_course_partially_update(self):
        """
        Staff user should be able to partially update a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory(code="COURSE-001", title="Course 001")
        organization = factories.OrganizationFactory(code="ORG-002")
        product = factories.ProductFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data={
                "title": "Updated Course 001",
                "organizations": [str(organization.id)],
                "product_relations": [
                    {
                        "product": str(product.id),
                        "organizations": [str(organization.id)],
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["title"], "Updated Course 001")
        self.assertEqual(content["organizations"][0]["code"], "ORG-002")
        self.assertEqual(len(content["product_relations"]), 1)

    def test_admin_api_course_delete(self):
        """
        Staff user should be able to delete a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/v1.0/admin/courses/{course.id}/")

        self.assertEqual(response.status_code, 204)
