"""
Test suite for User Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories


class UserAdminApiTest(TestCase):
    """
    Test suite for User Admin API.
    """

    def test_admin_api_user_request_without_authentication(self):
        """
        Anonymous users should not be able to request courses endpoint.
        """
        response = self.client.get("/api/v1.0/admin/users/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_user_request_with_lambda_user(self):
        """
        Lambda user should not be able to request users endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/users/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_user_list(self):
        """
        Staff user should not be able to get the full user list.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        users_count = random.randint(1, 10)
        factories.UserFactory.create_batch(users_count)

        response = self.client.get("/api/v1.0/admin/users/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_admin_api_user_list_filter_by_query(self):
        """
        Staff user should be able to list users by searching for their username, email
        or full_name.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        fonzie = factories.UserFactory(
            username="fnz",
            first_name="Fonzie",
            last_name="Fonzarelli",
            email="fonz@example.fr",
        )
        joanie = factories.UserFactory(
            username="jn",
            first_name="Joanie",
            last_name="Cunningham",
            email="joan@example.fr",
        )
        richie = factories.UserFactory(
            username="rch",
            first_name="Richie",
            last_name="Cunningham",
            email="rich@example.fr",
        )

        # An empty search should return no results
        response = self.client.get("/api/v1.0/admin/users/?query=")
        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 0)

        # Search by username
        response = self.client.get("/api/v1.0/admin/users/?query=fnz")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(
            content["results"][0],
            {
                "id": str(fonzie.id),
                "username": fonzie.username,
                "full_name": fonzie.get_full_name(),
            },
        )

        # Search by email
        response = self.client.get("/api/v1.0/admin/users/?query=@example.fr")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # Search by firstname
        response = self.client.get("/api/v1.0/admin/users/?query=joanie")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(
            content["results"][0],
            {
                "id": str(joanie.id),
                "username": joanie.username,
                "full_name": joanie.get_full_name(),
            },
        )

        # Search by lastname
        response = self.client.get("/api/v1.0/admin/users/?query=Cunningham")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["full_name"] for result in content["results"]],
            [character.get_full_name() for character in [joanie, richie]],
        )

    def test_admin_api_user_get(self):
        """
        Staff user should not be able to retrieve a user through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        user = factories.UserFactory()

        response = self.client.get(f"/api/v1.0/admin/users/{user.id}/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_admin_api_user_create(self):
        """
        Staff user should not be able to create a user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/users/")

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=405,
        )

    def test_admin_api_user_update(self):
        """
        Staff user should not be able to update a user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        user = factories.UserFactory()

        response = self.client.put(f"/api/v1.0/admin/users/{user.id}/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_admin_api_user_partially_update(self):
        """
        Staff user should not be able to partially update a user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        user = factories.UserFactory()

        response = self.client.patch(f"/api/v1.0/admin/users/{user.id}/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_admin_api_user_delete(self):
        """
        Staff user should not be able to delete a user.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        user = factories.UserFactory()

        response = self.client.delete(f"/api/v1.0/admin/users/{user.id}/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
