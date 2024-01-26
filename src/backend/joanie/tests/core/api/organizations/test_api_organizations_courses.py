"""
Test suite for Organization's courses API endpoint.
"""
import random
from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationCourseApiTest(BaseAPITestCase):
    """
    Test suite for Organization's courses API endpoint.
    """

    def test_api_organizations_courses_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of an organization's courses for
        anonymous users.
        """

        organization = factories.OrganizationFactory.create()
        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/courses/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organizations_courses_read_list_authenticated(self):
        """
        Get all courses from an organization
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Create 3 courses for two different organizations:
        # - course_0 has 2 course runs, one listed and one not listed
        # - course_1 has 1 course run, not listed
        # - course_2 has no course run
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        courses_without_rights = factories.CourseFactory.create_batch(
            3, organizations=[organizations[1]]
        )
        factories.CourseRunFactory(course=courses_without_rights[0], is_listed=False)
        factories.CourseRunFactory(course=courses_without_rights[0], is_listed=True)
        factories.CourseRunFactory(course=courses_without_rights[1], is_listed=False)

        # User has access to only one organization
        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )

        # Retrieve all courses from org with access
        with self.assertNumQueries(98):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/courses/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # It should return all courses from the first org
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {str(x["id"]) for x in content["results"]},
            {str(x.id) for x in courses},
        )

    def test_api_organizations_courses_read_list_without_access(self):
        """
        Get no courses when the user lists courses from an org without having
        access to it
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Create 3 courses:
        # - course_0 has 2 course runs, one listed and one not listed
        # - course_1 has 1 course run, not listed
        # - course_2 has no course run
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        with self.assertNumQueries(1):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[1].id}"
                    "/courses/?has_listed_course_runs=true"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/courses/?has_listed_course_runs=false",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[1].id}/courses/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[1].id}/courses/{courses[0].id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_organizations_courses_read_details_authenticated(self):
        """
        Get a specific courses from an organization
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )
        with self.assertNumQueries(51):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/courses/{courses[0].id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(courses[0].id))

    def test_api_organizations_courses_read_details_without_access(self):
        """
        Unauthorized uset cannot get a specific courses from an organization
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        factories.UserOrganizationAccessFactory(organization=organizations[0])
        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/courses/{courses[0].id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_organizations_courses_read_details_anonymous(self):
        """
        Unauthenticated cannot get a specific courses from an organization
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        factories.UserOrganizationAccessFactory(organization=organizations[0])
        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/courses/{courses[0].id}/",
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organizations_courses_read_list_has_listed_course_runs(self):
        """
        Get all courses from an organization with listed course runs
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Create 3 courses:
        # - course_0 has 2 course runs, one listed and one not listed
        # - course_1 has 1 course run, not listed
        # - course_2 has no course run
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(
            3, organizations=[organizations[0]]
        )
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        # User has access to only one organization
        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )

        # Retrieve all courses from org with listed course runs
        with self.assertNumQueries(52):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}"
                    "/courses/?has_listed_course_runs=true"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        # It should return only the course with a listed CourseRun
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(courses[0].id))

    def test_api_organizations_courses_create_authenticated(self):
        """
        Authenticated users should not be able to create a course.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)
        organization = factories.OrganizationFactory.create()

        data = {
            "code": "COU-001",
            "title": "Course 001",
        }

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/courses/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertFalse(models.Course.objects.exists())

    def test_api_organizations_courses_create_anonymous(self):
        """
        Anonymous users should not be able to create a course.
        """
        organization = factories.OrganizationFactory.create()

        data = {
            "code": "COU-001",
            "title": "Course 001",
        }

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/courses/",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organizations_courses_update_authenticated(self):
        """
        Anonymous users should not be able to update a course.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])
        data = {
            "code": "notacode",
            "title": "Not a course",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertFalse(models.Course.objects.filter(code="notacode").exists())

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_organizations_courses_update_anonymous(self):
        """
        Anonymous users should not be able to update a course.
        """
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])
        data = {
            "code": "notacode",
            "title": "Not a course",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_organizations_courses_patch_authenticated(self):
        """
        Anonymous users should not be able to patch a course.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])
        data = {
            "code": "notacode",
        }

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertFalse(models.Course.objects.filter(code="notacode").exists())

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_organizations_courses_patch_anonymous(self):
        """
        Anonymous users should not be able to patch a course.
        """
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])
        data = {
            "code": "notacode",
        }

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_organizations_courses_delete_authenticated(self):
        """
        Anonymous users should not be able to delete a course.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertTrue(models.Course.objects.filter(id=course.id).exists())

    def test_api_organizations_courses_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course.
        """
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory(organizations=[organization])

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/courses/{course.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        self.assertTrue(models.Course.objects.filter(id=course.id).exists())
