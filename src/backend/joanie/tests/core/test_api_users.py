"""
Test suite for User API.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class UserApiTest(BaseAPITestCase):
    """
    Test suite for User API.
    """

    def test_api_user_me_anonymous(self):
        """
        Anonymous users should not be able to get user information
        """
        factories.UserFactory()
        response = self.client.get("/api/v1.0/users/me/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_user_root_route(self):
        """
        Global user route should not exist
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/users/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_user_me_no_access(self):
        """
        User should see their infos on the me route
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.get_full_name(),
                "is_superuser": False,
                "is_staff": False,
                "abilities": {
                    "delete": False,
                    "get": True,
                    "patch": True,
                    "put": True,
                    "has_course_access": False,
                    "has_organization_access": False,
                },
            },
        )

    def test_api_user_me_course_access(self):
        """
        User should see their infos with the correct course
        accesses on the /me route
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)
        factories.UserCourseAccessFactory(user=user)

        response = self.client.get(
            "/api/v1.0/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.get_full_name(),
                "is_superuser": False,
                "is_staff": False,
                "abilities": {
                    "delete": False,
                    "get": True,
                    "patch": True,
                    "put": True,
                    "has_course_access": True,
                    "has_organization_access": False,
                },
            },
        )

    def test_api_user_me_organization_access(self):
        """
        User should see their infos with the correct organization
        accesses on the /me route
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(user=user)

        response = self.client.get(
            "/api/v1.0/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.get_full_name(),
                "is_superuser": False,
                "is_staff": False,
                "abilities": {
                    "delete": False,
                    "get": True,
                    "patch": True,
                    "put": True,
                    "has_course_access": False,
                    "has_organization_access": True,
                },
            },
        )
