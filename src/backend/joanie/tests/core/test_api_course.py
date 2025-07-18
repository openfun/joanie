"""
Test suite for Course API endpoint.
"""

import random
from http import HTTPStatus
from unittest import mock

from timedelta_isoformat import timedelta as timedelta_isoformat

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseApiTest(BaseAPITestCase):
    """
    Test suite for Course API endpoint.
    """

    maxDiff = None

    def test_api_course_list_anonymous(self):
        """
        Anonymous users should not be able to list courses.
        """
        factories.CourseFactory()
        response = self.client.get("/api/v1.0/courses/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
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

        with self.record_performance():
            response = self.client.get(
                "/api/v1.0/courses/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
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
                        "effort": timedelta_isoformat(
                            seconds=course.effort.total_seconds()
                        ).isoformat(),
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
                        "product_ids": [
                            str(product.id) for product in course.products.all()
                        ],
                        "course_run_ids": [
                            str(course_run.id)
                            for course_run in course.course_runs.all()
                        ],
                        "state": course.state,
                    }
                ],
            },
        )
        mock_abilities.called_once_with(user)

    def test_api_course_list_filter_has_listed_course_runs(self):
        """
        Authenticated users should be able to filter courses by whether they have
        listed course runs if they have access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Create 3 courses :
        # - course_0 has 2 course runs, one listed and one not listed
        # - course_1 has 1 course run, not listed
        # - course_2 has no course run
        courses = factories.CourseFactory.create_batch(3)
        factories.CourseRunFactory(course=courses[0], is_listed=False)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[0], is_listed=True)
        factories.CourseRunFactory(course=courses[1], is_listed=False)
        factories.CourseRunFactory(course=courses[1], is_listed=False)

        # Give user access to all courses
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)

        # Retrieve courses with listed course runs
        response = self.client.get(
            "/api/v1.0/courses/?has_listed_course_runs=true",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # It should return courses[0] only
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(courses[0].id))

        # Retrieve courses without listed course runs
        response = self.client.get(
            "/api/v1.0/courses/?has_listed_course_runs=false",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # It should return courses[1] and courses[2]
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(courses[1].id), str(courses[2].id)],
        )

    def test_api_course_list_filter_type(self):
        """
        Authenticated users should be able to filter courses by product
        type if they have access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        courses = factories.CourseFactory.create_batch(6)
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=courses[0:3]
        )
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT, courses=courses[3:5]
        )
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE, courses=courses[4::]
        )
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        response = self.client.get(
            f"/api/v1.0/courses/?product_type={enums.PRODUCT_TYPE_CREDENTIAL}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        response = self.client.get(
            f"/api/v1.0/courses/?product_type={enums.PRODUCT_TYPE_ENROLLMENT}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        response = self.client.get(
            f"/api/v1.0/courses/?product_type={enums.PRODUCT_TYPE_CERTIFICATE}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[courses[4]]
        )
        response = self.client.get(
            f"/api/v1.0/courses/?product_type={enums.PRODUCT_TYPE_CREDENTIAL}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

    def test_api_course_get_anonymous(self):
        """
        Anonymous users should not be allowed to get a course through its id.
        """
        course = factories.CourseFactory()

        response = self.client.get(f"/api/v1.0/courses/{course.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
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

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertDictEqual(
            response.json(), {"detail": "No Course matches the given query."}
        )

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
        factories.OfferingFactory(
            course=course,
            product=factories.ProductFactory(),
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertDictEqual(
            content,
            {
                "created_on": course.created_on.isoformat().replace("+00:00", "Z"),
                "code": course.code,
                "id": str(course.id),
                "cover": "_this_field_is_mocked",
                "effort": timedelta_isoformat(
                    seconds=course.effort.total_seconds()
                ).isoformat(),
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
                "product_ids": [str(product.id) for product in course.products.all()],
                "course_run_ids": [
                    str(course_run.id) for course_run in course.course_runs.all()
                ],
                "state": course.state,
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_get_authenticated_by_code(self, _):
        """
        Authenticated users should be able to get a course through its code
        if they have access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        course = factories.CourseFactory(code="MYCODE-0088")
        factories.UserCourseAccessFactory(user=user, course=course)
        factories.OfferingFactory(
            course=course,
            product=factories.ProductFactory(),
            organizations=[factories.OrganizationFactory()],
        )

        with self.record_performance():
            response = self.client.get(
                "/api/v1.0/courses/mycode-0088/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))

    def test_api_course_create_anonymous(self):
        """
        Anonymous users should not be able to create a course.
        """
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post("/api/v1.0/courses/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
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

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
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

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertDictEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

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

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertDictEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        course.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(course, key))

    def test_api_course_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course.
        """
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/v1.0/courses/{course.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
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

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
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

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_filter_query_by_course_title(self):
        """
        Authenticated users should be able to filter courses by their title if they have
        access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        course_1 = factories.CourseFactory(
            title="Introduction to resource filtering", code="MYCODE-0090"
        )
        course_2 = factories.CourseFactory(
            title="Advanced aerodynamic flows", code="MYCODE-0091"
        )
        course_3 = factories.CourseFactory(
            title="Rubber management on a single-seater", code="MYCODE-0092"
        )
        course_without_user_access = factories.CourseFactory(
            title="Drag reduce system optimization", code="MYCODE-0010"
        )
        course_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de ressource"
        )
        course_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        course_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )

        # Give user access to all courses
        for course in [course_1, course_2, course_3]:
            factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.get(
            "/api/v1.0/courses/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        queries = [
            "Flux aérodynamiques avancés",
            "Flux+aérodynamiques+avancés",
            "aérodynamiques",
            "aerodynamic",
            "aéro",
            "aero",
            "aer",
            "advanced",
            "flows",
            "flo",
            "Advanced aerodynamic flows",
            "dynamic",
            "ows",
            "av",
            "ux",
        ]

        # Retrieve only the course with the title 'Advanced aerodynamic flows'
        # that our user has access to.
        for query in queries:
            response = self.client.get(
                f"/api/v1.0/courses/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0].get("id"), str(course_2.id))

        # User type the title of a course he does not have access to
        response = self.client.get(
            f"/api/v1.0/courses/?query={course_without_user_access.title}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # User type the title of a course that does not exist at all
        response = self.client.get(
            "/api/v1.0/courses/?query=veryFakeCourseTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_course_filter_query_by_course_code(self):
        """
        Authenticated users should be able to filter courses by their code if they have
        access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course_1 = factories.CourseFactory(
            title="Introduction to resource filtering", code="MYCODE-0990"
        )
        course_2 = factories.CourseFactory(
            title="Advanced aerodynamic flows", code="MYCODE-0991"
        )
        course_3 = factories.CourseFactory(
            title="Rubber management on a single-seater", code="MYCODE-0992"
        )
        course_without_user_access = factories.CourseFactory(
            title="Drag reduce system optimization", code="MYCODE-0993"
        )
        factories.CourseFactory(
            title="Single-seater porpoising introduction", code="MYCODE-0994"
        )
        # Give user access to all courses except 'course_without_user_access'
        for course in [course_1, course_2, course_3]:
            factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.get(
            f"/api/v1.0/courses/?query={course_1.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(course_1.id))

        # Retrieve 3 courses because only the last characters changes
        response = self.client.get(
            f"/api/v1.0/courses/?query={course_1.code[:1]}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        # Parsing nothing in query should return all courses that the user has access to
        response = self.client.get(
            "/api/v1.0/courses/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(course_1.id), str(course_2.id), str(course_3.id)],
        )

        # User searches with a course code that does not exists
        response = self.client.get(
            "/api/v1.0/courses/?query=fakeCourseCode",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # User searches with a course code where he does not have access
        response = self.client.get(
            f"/api/v1.0/courses/?query={course_without_user_access.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)
