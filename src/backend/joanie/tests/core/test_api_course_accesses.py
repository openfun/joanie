"""
Tests course access API endpoints in Joanie's core app.
"""
import random
from unittest import mock
from uuid import uuid4

from rest_framework.pagination import PageNumberPagination

from joanie.core import factories
from joanie.core.models import CourseAccess
from joanie.core.serializers import CourseAccessSerializer
from joanie.tests.base import BaseAPITestCase

# pylint: disable=too-many-public-methods, too-many-lines


class CourseAccessesAPITestCase(BaseAPITestCase):
    """Test requests on joanie's core app course access API endpoint."""

    # List

    def test_api_course_accesses_list_anonymous(self):
        """Anonymous users should not be allowed to list course accesses."""
        access = factories.UserCourseAccessFactory()

        response = self.client.get(f"/api/v1.0/courses/{access.course.id!s}/accesses/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_accesses_list_authenticated_not_related(self):
        """
        Authenticated users should not be allowed to list course accesses for a
        course to which they are not related.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        factories.UserCourseAccessFactory(course=course)
        factories.UserCourseAccessFactory(course=course, role="administrator")
        factories.UserCourseAccessFactory(course=course, role="instructor")
        factories.UserCourseAccessFactory(course=course, role="manager")
        factories.UserCourseAccessFactory(course=course, role="owner")

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_api_course_accesses_list_authenticated_instructor(self):
        """
        Authenticated users should be allowed to list course accesses for a course
        in which they are only instructor.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        course_accesses = (
            # Access for the logged in user
            factories.UserCourseAccessFactory(
                course=course, user=user, role="instructor"
            ),
            # Accesses for other users
            factories.UserCourseAccessFactory(course=course, role="administrator"),
            factories.UserCourseAccessFactory(course=course, role="instructor"),
            factories.UserCourseAccessFactory(course=course, role="manager"),
            factories.UserCourseAccessFactory(course=course, role="owner"),
        )

        # Accesses related to another course should not be listed
        other_course = factories.CourseFactory()
        # Access for the logged in user
        factories.UserCourseAccessFactory(
            course=other_course, user=user, role="instructor"
        )
        # Accesses for other users
        factories.UserCourseAccessFactory(course=other_course, role="administrator")
        factories.UserCourseAccessFactory(course=other_course, role="instructor")
        factories.UserCourseAccessFactory(course=other_course, role="manager")
        factories.UserCourseAccessFactory(course=other_course, role="owner")

        with self.assertNumQueries(3):
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 5)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in course_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_course_accesses_list_authenticated_manager(self):
        """
        Authenticated users should be allowed to list course accesses for a course
        in which they are only manager.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        course_accesses = (
            # Access for the logged in user
            factories.UserCourseAccessFactory(course=course, user=user, role="manager"),
            # Accesses for other users
            factories.UserCourseAccessFactory(course=course),
            factories.UserCourseAccessFactory(course=course, role="administrator"),
            factories.UserCourseAccessFactory(course=course, role="instructor"),
            factories.UserCourseAccessFactory(course=course, role="manager"),
            factories.UserCourseAccessFactory(course=course, role="owner"),
        )

        # Accesses related to another course should not be listed
        other_course = factories.CourseFactory()
        # Access for the logged in user
        factories.UserCourseAccessFactory(
            course=other_course, user=user, role="manager"
        )
        # Accesses for other users
        factories.UserCourseAccessFactory(course=other_course)
        factories.UserCourseAccessFactory(course=other_course, role="administrator")
        factories.UserCourseAccessFactory(course=other_course, role="instructor")
        factories.UserCourseAccessFactory(course=other_course, role="manager")
        factories.UserCourseAccessFactory(course=other_course, role="owner")

        response = self.client.get(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 6)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in course_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_course_accesses_list_authenticated_administrator(self):
        """
        Authenticated users should be allowed to list course accesses for a course
        in which they are administrator.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        course_accesses = (
            # Access for the logged in user
            factories.UserCourseAccessFactory(
                course=course, user=user, role="administrator"
            ),
            # Accesses for other users
            factories.UserCourseAccessFactory(course=course),
            factories.UserCourseAccessFactory(course=course, role="administrator"),
            factories.UserCourseAccessFactory(course=course, role="instructor"),
            factories.UserCourseAccessFactory(course=course, role="manager"),
            factories.UserCourseAccessFactory(course=course, role="owner"),
        )

        # Accesses related to another course should not be listed
        other_course = factories.CourseFactory()
        # Access for the logged in user
        factories.UserCourseAccessFactory(
            course=other_course, user=user, role="administrator"
        )
        # Accesses for other users
        factories.UserCourseAccessFactory(course=other_course)
        factories.UserCourseAccessFactory(course=other_course, role="administrator")
        factories.UserCourseAccessFactory(course=other_course, role="instructor")
        factories.UserCourseAccessFactory(course=other_course, role="manager")
        factories.UserCourseAccessFactory(course=other_course, role="owner")

        response = self.client.get(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 6)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in course_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_course_accesses_list_authenticated_owner(self):
        """
        Authenticated users should be allowed to list course accesses for a course
        in which they are owner.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        course_accesses = (
            # Access for the logged in user
            factories.UserCourseAccessFactory(course=course, user=user, role="owner"),
            # Accesses for other users
            factories.UserCourseAccessFactory(course=course),
            factories.UserCourseAccessFactory(course=course, role="administrator"),
            factories.UserCourseAccessFactory(course=course, role="instructor"),
            factories.UserCourseAccessFactory(course=course, role="manager"),
            factories.UserCourseAccessFactory(course=course, role="owner"),
        )

        # Accesses related to another course should not be listed
        other_course = factories.CourseFactory()
        # Access for the logged in user
        factories.UserCourseAccessFactory(
            course=other_course, user=user, role="administrator"
        )
        # Accesses for other users
        factories.UserCourseAccessFactory(course=other_course)
        factories.UserCourseAccessFactory(course=other_course, role="administrator")
        factories.UserCourseAccessFactory(course=other_course, role="instructor")
        factories.UserCourseAccessFactory(course=other_course, role="manager")
        factories.UserCourseAccessFactory(course=other_course, role="owner")

        response = self.client.get(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 6)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in course_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_course_accesses_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""

        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        accesses = [
            factories.UserCourseAccessFactory(
                course=course,
                user=user,
                role=random.choice(["administrator", "owner"]),
            ),
            *factories.UserCourseAccessFactory.create_batch(2, course=course),
        ]
        access_ids = [str(access.id) for access in accesses]

        response = self.client.get(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"],
            f"http://testserver/api/v1.0/courses/{course.id!s}/accesses/?page=2",
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            access_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            f"/api/v1.0/courses/{course.id!s}/accesses/?page=2",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"],
            f"http://testserver/api/v1.0/courses/{course.id!s}/accesses/",
        )

        self.assertEqual(len(content["results"]), 1)
        access_ids.remove(content["results"][0]["id"])
        self.assertEqual(access_ids, [])

    # Retrieve

    def test_api_course_accesses_retrieve_anonymous(self):
        """
        Anonymous users should not be allowed to retrieve a course access.
        """
        access = factories.UserCourseAccessFactory()
        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_accesses_retrieve_authenticated_not_related(self):
        """
        Authenticated users should not be allowed to retrieve a course access for
        a course to which they are not related.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        self.assertEqual(len(CourseAccess.ROLE_CHOICES), 4)

        for role, _name in CourseAccess.ROLE_CHOICES:
            access = factories.UserCourseAccessFactory(course=course, role=role)
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json(),
                {"detail": "You do not have permission to perform this action."},
            )

    def test_api_course_accesses_retrieve_authenticated_instructor(self):
        """
        A user who is an instructor of a course should be allowed to retrieve the
        associated course accessesnly instructor.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(
            users=[(user, "instructor")],
        )
        self.assertEqual(len(CourseAccess.ROLE_CHOICES), 4)

        for role, _name in CourseAccess.ROLE_CHOICES:
            access = factories.UserCourseAccessFactory(course=course, role=role)
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user_id": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_course_accesses_retrieve_authenticated_manager(self):
        """
        A user who is a manager of a course should be allowed to retrieve the
        associated course accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(
            users=[(user, "manager")],
        )
        self.assertEqual(len(CourseAccess.ROLE_CHOICES), 4)

        for role, _name in CourseAccess.ROLE_CHOICES:
            access = factories.UserCourseAccessFactory(course=course, role=role)
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user_id": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_course_accesses_retrieve_authenticated_administrator(self):
        """
        A user who is a administrator of a course should be allowed to retrieve the
        associated course accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        self.assertEqual(len(CourseAccess.ROLE_CHOICES), 4)

        for role, _name in CourseAccess.ROLE_CHOICES:
            access = factories.UserCourseAccessFactory(course=course, role=role)
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user_id": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_course_accesses_retrieve_authenticated_owner(self):
        """
        A user who is a direct owner of a course should be allowed to retrieve the
        associated course accesses
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "owner")])
        self.assertEqual(len(CourseAccess.ROLE_CHOICES), 4)

        for role, _name in CourseAccess.ROLE_CHOICES:
            access = factories.UserCourseAccessFactory(course=course, role=role)
            response = self.client.get(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user_id": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_course_accesses_retrieve_authenticated_wrong_course(
        self,
    ):
        """The course in the url should match the targeted access."""
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course, other_course = factories.CourseFactory.create_batch(2, users=[user])
        access = factories.UserCourseAccessFactory(course=course)

        response = self.client.get(
            f"/api/v1.0/courses/{other_course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 404)

    # Create

    def test_api_course_accesses_create_anonymous(self):
        """Anonymous users should not be allowed to create course accesses."""
        user = factories.UserFactory()
        course = factories.CourseFactory()

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(user.id),
                "role": random.choice(
                    ["administrator", "instructor", "manager", "owner"]
                ),
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        self.assertFalse(CourseAccess.objects.exists())

    def test_api_course_accesses_create_authenticated(self):
        """Authenticated users should not be allowed to create course accesses."""
        user, other_user = factories.UserFactory.create_batch(2)
        course = factories.CourseFactory()

        jwt_token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": random.choice(
                    ["administrator", "instructor", "manager", "owner"]
                ),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": ("You are not allowed to manage accesses for this course.")},
        )
        self.assertFalse(CourseAccess.objects.filter(user=other_user).exists())

    def test_api_course_accesses_create_instructors(self):
        """
        A user who is a simple instructor in a course should not be allowed to create
        course accesses in this course.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        course = factories.CourseFactory(users=[(user, "instructor")])

        jwt_token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": random.choice(
                    ["administrator", "instructor", "manager", "owner"]
                ),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": ("You are not allowed to manage accesses for this course.")},
        )
        self.assertFalse(CourseAccess.objects.filter(user=other_user).exists())

    def test_api_course_accesses_create_managers(self):
        """
        A user who is a simple manager in a course should not be allowed to create
        course accesses in this course.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        course = factories.CourseFactory(users=[(user, "manager")])

        jwt_token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": random.choice(
                    ["administrator", "instructor", "manager", "owner"]
                ),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": ("You are not allowed to manage accesses for this course.")},
        )
        self.assertFalse(CourseAccess.objects.filter(user=other_user).exists())

    def test_api_course_accesses_create_administrators_except_owner(self):
        """
        A user who is administrator in a course should be allowed to create course
        accesses in this course for roles other than owner (which is tested in the
        subsequent test).
        """
        user, other_user = factories.UserFactory.create_batch(2)
        course = factories.CourseFactory(users=[(user, "administrator")])

        jwt_token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": random.choice(["instructor", "manager", "administrator"]),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=other_user).exists())

    def test_api_course_accesses_create_administrators_owner(self):
        """
        A user who is administrator in a course should not be allowed to create
        course accesses in this course for the owner role.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        course = factories.CourseFactory(users=[(user, "administrator")])

        jwt_token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": "owner",
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseAccess.objects.filter(user=other_user).exists())

    def test_api_course_accesses_create_owner_all_roles(self):
        """
        A user who is owner in a course should be allowed to create
        course accesses in this course for all roles.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "owner")])

        jwt_token = self.generate_token_from_user(user)

        for i, role in enumerate(["administrator", "instructor", "manager", "owner"]):
            other_user = factories.UserFactory()
            response = self.client.post(
                f"/api/v1.0/courses/{course.id!s}/accesses/",
                {
                    "user_id": str(other_user.id),
                    "role": role,
                },
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 201)
            self.assertEqual(CourseAccess.objects.count(), i + 2)
            self.assertTrue(CourseAccess.objects.filter(user=other_user).exists())

    # Update

    def test_api_course_accesses_update_anonymous(self):
        """Anonymous users should not be allowed to update a course access."""
        access = factories.UserCourseAccessFactory()
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory().id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_authenticated(self):
        """Authenticated users should not be allowed to update a course access."""
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        access = factories.UserCourseAccessFactory()
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "instructor")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_instructor(self):
        """
        A user who is only instructor in a course should not be allowed to update
        a user access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "instructor")])
        access = factories.UserCourseAccessFactory(course=course)
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "instructor")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_manager(self):
        """
        A user who is only manager in a course should not be allowed to update
        a user access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "manager")])
        access = factories.UserCourseAccessFactory(course=course)
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "manager")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_administrator_except_owner(self):
        """
        A user who is an administrator in a course should be allowed to update a user
        access for this course, as long as s.he does not try to set the role to owner.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(["administrator", "instructor", "manager"]),
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data=new_data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            if (
                new_data["role"] == old_values["role"]
            ):  # we are not not really updating the role
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_administrator_from_owner(self):
        """
        A user who is an administrator in a course, should not be allowed to update
        the user access of an owner for this course.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course, user=other_user, role="owner"
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_administrator_to_owner(self):
        """
        A user who is an administrator in a course, should not be allowed to update
        the user access of another user when granting ownership.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course,
            user=other_user,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": "owner",
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data=new_data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            # We are not allowed or not really updating the role
            if field == "role" or new_data["role"] == old_values["role"]:
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_owner_except_owner(self):
        """
        A user who is an owner in a course should be allowed to update
        a user access for this course except for existing owner accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(
            course=course,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data=new_data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            if (
                new_data["role"] == old_values["role"]
            ):  # we are not really updating the role
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data

            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_owner_for_owners(self):
        """
        A user who is an owner in a course should not be allowed to update
        an existing owner access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(course=course, role="owner")
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }
        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_update_owner_self(self):
        """
        A user who is an owner of a course should be allowed to update
        her own user access provided there are other owners in the course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        access = factories.UserCourseAccessFactory(
            course=course, user=user, role="owner"
        )
        old_values = CourseAccessSerializer(instance=access).data
        new_role = random.choice(["administrator", "instructor", "manager"])

        response = self.client.put(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            data={**old_values, "role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        access.refresh_from_db()
        self.assertEqual(access.role, "owner")

        # Add another owner and it should now work
        factories.UserCourseAccessFactory(course=course, role="owner")

        response = self.client.put(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            data={**old_values, "role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        access.refresh_from_db()
        self.assertEqual(access.role, new_role)

    # Patch

    def test_api_course_accesses_patch_anonymous(self):
        """Anonymous users should not be allowed to patch a course access."""
        access = factories.UserCourseAccessFactory()
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory().id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_authenticated(self):
        """Authenticated users should not be allowed to patch a course access."""
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        access = factories.UserCourseAccessFactory()
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "instructor")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_instructor(self):
        """
        A user who is a simple instructor in a course should not be allowed to update
        a user access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "instructor")])
        access = factories.UserCourseAccessFactory(course=course)
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "instructor")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_manager(self):
        """
        A user who is a simple manager in a course should not be allowed to update
        a user access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "manager")])
        access = factories.UserCourseAccessFactory(course=course)
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "manager")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_administrator_except_owner(self):
        """
        A user who is an administrator in a course should be allowed to patch a user
        access for this course, as long as s.he does not try to set the role to owner.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(["administrator", "instructor", "manager"]),
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            if field == "role" and value == old_values["role"]:
                # We are not really updating the role
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertDictEqual(updated_values, old_values)

    def test_api_course_accesses_patch_administrator_from_owner(self):
        """
        A user who is an administrator in a course, should not be allowed to patch
        the user access of an owner for this course.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course, user=other_user, role="owner"
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_administrator_to_owner(self):
        """
        A user who is an administrator in a course, should not be allowed to patch
        the user access of another user when granting ownership.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course,
            user=other_user,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": "owner",
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            if field == "role":
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_owner_except_owner(self):
        """
        A user who is an owner in a course should be allowed to patch
        a user access for this course except for existing owner accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(
            course=course,
            role=random.choice(["administrator", "instructor", "manager"]),
        )
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            if field == "role" and value == old_values["role"]:
                # We are not really updating the role
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data

            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_owner_for_owners(self):
        """
        A user who is an owner in a course should not be allowed to patch
        an existing owner access for this course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(course=course, role="owner")
        old_values = CourseAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "course_id": factories.CourseFactory(users=[(user, "administrator")]).id,
            "user_id": factories.UserFactory().id,
            "role": random.choice(CourseAccess.ROLE_CHOICES)[0],
        }
        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)

            access.refresh_from_db()
            updated_values = CourseAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_course_accesses_patch_owner_self(self):
        """
        A user who is an owner of a course should be allowed to patch
        her own user access provided there are other owners in the course.
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        course = factories.CourseFactory()
        access = factories.UserCourseAccessFactory(
            course=course, user=user, role="owner"
        )
        new_role = random.choice(["administrator", "instructor", "manager"])

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            data={"role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        access.refresh_from_db()
        self.assertEqual(access.role, "owner")

        # Add another owner and it should now work
        factories.UserCourseAccessFactory(course=course, role="owner")

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            data={"role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        access.refresh_from_db()
        self.assertEqual(access.role, new_role)

    # Delete

    def test_api_course_accesses_delete_anonymous(self):
        """Anonymous users should not be allowed to destroy a course access."""
        access = factories.UserCourseAccessFactory()

        response = self.client.delete(
            f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(CourseAccess.objects.count(), 1)

    def test_api_course_accesses_delete_authenticated(self):
        """
        Authenticated users should not be allowed to delete a course access for a
        course in which they are not administrator.
        """
        access = factories.UserCourseAccessFactory()
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/courses/{access.course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CourseAccess.objects.count(), 1)

    def test_api_course_accesses_delete_instructors(self):
        """
        Authenticated users should not be allowed to delete a course access for a
        course in which they are a simple instructor.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "instructor")])
        access = factories.UserCourseAccessFactory(course=course)

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CourseAccess.objects.count(), 2)

    def test_api_course_accesses_delete_managers(self):
        """
        Authenticated users should not be allowed to delete a course access for a
        course in which they are only a manager.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "manager")])
        access = factories.UserCourseAccessFactory(course=course)

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CourseAccess.objects.count(), 2)

    def test_api_course_accesses_delete_administrators(self):
        """
        Users who are administrators in a course should be allowed to delete a user access
        from the course provided it is not ownership.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "administrator")])
        access = factories.UserCourseAccessFactory(
            course=course, role=random.choice(["instructor", "administrator"])
        )

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(CourseAccess.objects.count(), 1)

    def test_api_course_accesses_delete_owners_except_owners(self):
        """
        Users should be able to delete the course access of another user
        for a course of which they are owner except for owners.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(
            course=course, role=random.choice(["instructor", "administrator"])
        )

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(CourseAccess.objects.count(), 1)

    def test_api_course_accesses_delete_owners_for_owners(self):
        """
        Users should not be able to delete the course access of another owner
        even for a course in which they are direct owner.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory(users=[(user, "owner")])
        access = factories.UserCourseAccessFactory(course=course, role="owner")

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 2)
        self.assertTrue(CourseAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CourseAccess.objects.count(), 2)

    def test_api_course_accesses_delete_owners_last_owner(self):
        """
        It should not be possible to delete the last owner access from a course
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        access = factories.UserCourseAccessFactory(
            course=course, user=user, role="owner"
        )

        jwt_token = self.generate_token_from_user(user)

        self.assertEqual(CourseAccess.objects.count(), 1)
        response = self.client.delete(
            f"/api/v1.0/courses/{course.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CourseAccess.objects.count(), 1)
