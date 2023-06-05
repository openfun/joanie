"""
Test suite for Course API endpoint.
"""
import random
from unittest import mock

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseApiTest(BaseAPITestCase):
    """
    Test suite for Course API endpoint.
    """

    def test_api_course_list_anonymous(self):
        """
        Anonymous users should not be able to list courses.
        """
        factories.CourseFactory()
        response = self.client.get("/api/v1.0/courses/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_list_authenticated_queries(self):
        """
        Authenticated users should only see the courses to which they have access.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        factories.CourseFactory()
        courses = factories.CourseFactory.create_batch(3)
        factories.UserCourseAccessFactory(user=user, course=courses[0])
        factories.UserCourseAccessFactory(user=user, course=courses[1])

        with self.assertNumQueries(16):
            response = self.client.get(
                "/api/v1.0/courses/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(course.id) for course in courses[:2]],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_list_authenticated_format(self, _):
        """
        Authenticated users should only see the courses to which they have access.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        factories.CourseFactory()
        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(user=user, course=course)

        with mock.patch.object(
            models.Course, "get_abilities", return_value={"foo": "bar"}
        ) as mock_abilities:
            response = self.client.get(
                "/api/v1.0/courses/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "created_on": course.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "abilities": {"foo": "bar"},
                        "code": course.code,
                        "id": str(course.id),
                        "cover": "_this_field_is_mocked",
                        "title": course.title,
                        "organizations": [
                            {
                                "code": organization.code,
                                "id": str(organization.id),
                                "logo": "_this_field_is_mocked",
                                "title": organization.title,
                            }
                            for organization in course.organizations.all()
                        ],
                        "selling_organizations": [],
                        "products": [
                            str(product.id) for product in course.products.all()
                        ],
                        "course_runs": [
                            str(course_run.id)
                            for course_run in course.course_runs.all()
                        ],
                        "state": course.state,
                    }
                ],
            },
        )
        mock_abilities.called_once_with(user)

    def test_api_course_get_anonymous(self):
        """
        Anonymous users should not be allowed to get a course through its id.
        """
        course = factories.CourseFactory()

        response = self.client.get(f"/api/v1.0/courses/{course.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_get_authenticated_no_access(self):
        """
        Authenticated users should not be able to get a course through its id
        if they have no access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_get_authenticated_with_access(self, _):
        """
        Authenticated users should be able to get a course through its id
        if they have access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(user=user, course=course)
        factories.CourseProductRelationFactory(
            course=course,
            product=factories.ProductFactory(),
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with self.assertNumQueries(10):
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertEqual(
            content,
            {
                "created_on": course.created_on.isoformat().replace("+00:00", "Z"),
                "code": course.code,
                "id": str(course.id),
                "cover": "_this_field_is_mocked",
                "title": course.title,
                "organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                    }
                    for organization in course.organizations.all()
                ],
                "selling_organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                    }
                    for organization in course.get_selling_organizations()
                ],
                "products": [str(product.id) for product in course.products.all()],
                "course_runs": [
                    str(course_run.id) for course_run in course.course_runs.all()
                ],
                "state": course.state,
            },
        )

    def test_api_course_create_anonymous(self):
        """
        Anonymous users should not be able to create a course.
        """
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post("/api/v1.0/courses/", data=data)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(models.Course.objects.exists())

    def test_api_course_create_authenticated(self):
        """
        Authenticated users should not be able to create a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post(
            "/api/v1.0/courses/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(models.Course.objects.exists())

    def test_api_course_update_anonymous(self):
        """
        Anonymous users should not be able to update a course.
        """
        course = factories.CourseFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(f"/api/v1.0/courses/{course.id}/", data=data)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_course_update_authenticated_without_access(self):
        """
        Authenticated users should not be able to update a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_course_update_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be able to update a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(
            user=user,
            course=course,
            role=enums.OWNER,
        )

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_course_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course.
        """
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/v1.0/courses/{course.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated_without_access(self):
        """
        Authenticated users should not be able to delete a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be able
        to delete a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(
            user=user,
            course=course,
            role=enums.OWNER,
        )

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)
