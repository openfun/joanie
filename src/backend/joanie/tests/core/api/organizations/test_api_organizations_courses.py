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
        with self.assertNumQueries(101):
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
        with self.assertNumQueries(52):
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
        with self.assertNumQueries(53):
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

    def test_api_organizations_courses_read_list_filter_by_query_by_course_title(self):
        """
        Authenticated user should be able to get specific courses by their title from an
        organization when the user has access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        organizations = factories.OrganizationFactory.create_batch(2)
        # Create courses
        course_1 = factories.CourseFactory(
            title="Introduction to resource filtering",
            organizations=[organizations[0]],
        )
        course_2 = factories.CourseFactory(
            title="Advanced aerodynamic flows",
            organizations=[organizations[0]],
        )
        course_3 = factories.CourseFactory(
            title="Rubber management on a single-seater",
            organizations=[organizations[0]],
        )
        course_4 = factories.CourseFactory(
            title="Drag reduce system optimization",
            organizations=[organizations[1]],
        )
        course_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de resource"
        )
        course_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        course_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )
        course_4.translations.create(
            language_code="fr-fr",
            title="Optimisation du système de réduction de la traînée",
        )
        # Create course run with the courses
        factories.CourseRunFactory(course=course_1, is_listed=False)
        factories.CourseRunFactory(course=course_1, is_listed=True)
        factories.CourseRunFactory(course=course_2, is_listed=False)
        factories.CourseRunFactory(course=course_3, is_listed=False)
        factories.CourseRunFactory(course=course_4, is_listed=True)
        # Give access to organization for the user
        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )
        factories.UserOrganizationAccessFactory(
            organization=organizations[1], user=user
        )

        # Prepare queries to test
        queries = [
            "Flux",
            "aérodynamiques",
            "avancés",
            "Advanced aerodynamic flows",
            "Advanced+aerodynamic+flows",
            "Flux aéro",
            "fl",
            "ux",
        ]
        # We should only find 1 Course : course_2
        for query in queries:
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/courses/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0].get("id"), str(course_2.id))

        # Prepare queries to test for the second organization : course_4
        queries = [
            "Optimisation du système de réduction de la traînée",
            "Drag reduce system optimization",
            "Optimisation",
            "drag",
            "system",
            "za",
            "de",
            "la",
        ]
        # We should only find 1 Course : course_
        for query in queries:
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[1].id}/courses/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(
                content["results"][0].get("id"),
                str(course_4.id),
            )

        # When parsing nothing, we should see the course_1, course_2 and course_3
        # from organization[0]
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/courses/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        # Retrieve the course from the second organization : we should find 1, course_4
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/courses/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_4.id)],
        )

        # We should get no result if we parse a fake Course title that does not exist
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/courses/?query=veryFakeCourseTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_organizations_courses_read_list_filter_by_query_by_course_code(self):
        """
        Authenticated user should be able to get a specific course by its code from an
        organization when the user has access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        organizations = factories.OrganizationFactory.create_batch(2)
        course_1 = factories.CourseFactory(
            code="MYCODE-0090", organizations=[organizations[0]]
        )
        course_2 = factories.CourseFactory(
            code="MYCODE-0091", organizations=[organizations[0]]
        )
        course_3 = factories.CourseFactory(
            code="MYCODE-0092", organizations=[organizations[0]]
        )
        course_4 = factories.CourseFactory(
            code="MYCODE-0093", organizations=[organizations[1]]
        )
        factories.CourseRunFactory(course=course_1, is_listed=False)
        factories.CourseRunFactory(course=course_1, is_listed=True)
        factories.CourseRunFactory(course=course_2, is_listed=False)
        factories.CourseRunFactory(course=course_3, is_listed=True)
        factories.CourseRunFactory(course=course_4, is_listed=True)

        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )
        factories.UserOrganizationAccessFactory(
            organization=organizations[1], user=user
        )

        # We should find the course_1 in return
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/courses/?query={course_1.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(course_1.id))

        # Retrieve 3 courses because only the last characters changes from that same organization
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/courses/?query={course_1.code[:1]}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        # When parsing nothing, we should find the 3 courses available by the organization[0]
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/courses/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        # Retrieve 1 course from the other organization (course_4)
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/courses/?query=MYCODE-009",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_4.id)],
        )

        # When parsing a fake course code, we should get no result.
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/courses/?query=veryFakeCourseCode",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)
