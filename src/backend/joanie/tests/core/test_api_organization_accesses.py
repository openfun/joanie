"""
Tests organization access API endpoints in Joanie's core app.
"""
import random
from unittest import mock
from uuid import uuid4

from rest_framework.pagination import PageNumberPagination

from joanie.core import factories
from joanie.core.models import OrganizationAccess
from joanie.core.serializers import OrganizationAccessSerializer
from joanie.tests.base import BaseAPITestCase

# pylint: disable=too-many-public-methods, too-many-lines


class OrganizationAccessesAPITestCase(BaseAPITestCase):
    """Test requests on joanie's core app organization access API endpoint."""

    # List

    def test_api_organization_accesses_list_anonymous(self):
        """Anonymous users should not be allowed to list organization accesses."""
        access = factories.UserOrganizationAccessFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{access.organization.id!s}/accesses/"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_accesses_list_authenticated_not_related(self):
        """
        Authenticated users should not be allowed to list organization accesses for an
        organization to which they are not related.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization)
        factories.UserOrganizationAccessFactory(
            organization=organization, role="member"
        )
        factories.UserOrganizationAccessFactory(
            organization=organization, role="administrator"
        )
        factories.UserOrganizationAccessFactory(organization=organization, role="owner")

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_api_organization_accesses_list_authenticated_member(self):
        """
        Authenticated users should be allowed to list organization accesses for an organization
        in which they are a simple member.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        organization_accesses = (
            # Access for the logged in user
            factories.UserOrganizationAccessFactory(
                organization=organization, user=user, role="member"
            ),
            # Accesses for other users
            factories.UserOrganizationAccessFactory(
                organization=organization, role="member"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="administrator"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="owner"
            ),
        )

        # Accesses related to another organization should not be listed
        other_organization = factories.OrganizationFactory()
        # Access for the logged in user
        factories.UserOrganizationAccessFactory(
            organization=other_organization, user=user, role="member"
        )
        # Accesses for other users
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="member"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="administrator"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="owner"
        )

        with self.assertNumQueries(3):
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 4)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in organization_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_organization_accesses_list_authenticated_administrator(self):
        """
        Authenticated users should be allowed to list organization accesses for an organization
        in which they are administrator.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        organization_accesses = (
            # Access for the logged in user
            factories.UserOrganizationAccessFactory(
                organization=organization, user=user, role="administrator"
            ),
            # Accesses for other users
            factories.UserOrganizationAccessFactory(organization=organization),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="member"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="administrator"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="owner"
            ),
        )

        # Accesses related to another organization should not be listed
        other_organization = factories.OrganizationFactory()
        # Access for the logged in user
        factories.UserOrganizationAccessFactory(
            organization=other_organization, user=user, role="administrator"
        )
        # Accesses for other users
        factories.UserOrganizationAccessFactory(organization=other_organization)
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="member"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="administrator"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="owner"
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 5)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in organization_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_organization_accesses_list_authenticated_owner(self):
        """
        Authenticated users should be allowed to list organization accesses for an organization
        in which they are owner.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        organization_accesses = (
            # Access for the logged in user
            factories.UserOrganizationAccessFactory(
                organization=organization, user=user, role="owner"
            ),
            # Accesses for other users
            factories.UserOrganizationAccessFactory(organization=organization),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="member"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="administrator"
            ),
            factories.UserOrganizationAccessFactory(
                organization=organization, role="owner"
            ),
        )

        # Accesses related to another organization should not be listed
        other_organization = factories.OrganizationFactory()
        # Access for the logged in user
        factories.UserOrganizationAccessFactory(
            organization=other_organization, user=user, role="administrator"
        )
        # Accesses for other users
        factories.UserOrganizationAccessFactory(organization=other_organization)
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="member"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="administrator"
        )
        factories.UserOrganizationAccessFactory(
            organization=other_organization, role="owner"
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 5)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(access.id) for access in organization_accesses],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_organization_accesses_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""

        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        accesses = [
            factories.UserOrganizationAccessFactory(
                organization=organization,
                user=user,
                role=random.choice(["administrator", "owner"]),
            ),
            *factories.UserOrganizationAccessFactory.create_batch(
                2, organization=organization
            ),
        ]
        access_ids = [str(access.id) for access in accesses]

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"],
            f"http://testserver/api/v1.0/organizations/{organization.id!s}/accesses/?page=2",
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            access_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/?page=2",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"],
            f"http://testserver/api/v1.0/organizations/{organization.id!s}/accesses/",
        )

        self.assertEqual(len(content["results"]), 1)
        access_ids.remove(content["results"][0]["id"])
        self.assertEqual(access_ids, [])

    # Retrieve

    def test_api_organization_accesses_retrieve_anonymous(self):
        """
        Anonymous users should not be allowed to retrieve an organization access.
        """
        access = factories.UserOrganizationAccessFactory()
        response = self.client.get(
            f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_accesses_retrieve_authenticated_not_related(self):
        """
        Authenticated users should not be allowed to retrieve an organization access for
        an organization to which they are not related.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        self.assertEqual(len(OrganizationAccess.ROLE_CHOICES), 3)

        for role, _name in OrganizationAccess.ROLE_CHOICES:
            access = factories.UserOrganizationAccessFactory(
                organization=organization, role=role
            )
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json(),
                {"detail": "You do not have permission to perform this action."},
            )

    def test_api_organization_accesses_retrieve_authenticated_member(self):
        """
        Authenticated users should not be allowed to retrieve an organization access for an
        organization in which they are a simple member.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(
            users=[(user, "member")],
        )
        self.assertEqual(len(OrganizationAccess.ROLE_CHOICES), 3)

        for role, _name in OrganizationAccess.ROLE_CHOICES:
            access = factories.UserOrganizationAccessFactory(
                organization=organization, role=role
            )
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_organization_accesses_retrieve_authenticated_administrator(self):
        """
        A user who is an administrator of an organization should be allowed to retrieve the
        associated organization accesses
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        self.assertEqual(len(OrganizationAccess.ROLE_CHOICES), 3)

        for role, _name in OrganizationAccess.ROLE_CHOICES:
            access = factories.UserOrganizationAccessFactory(
                organization=organization, role=role
            )
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "user": str(access.user.id),
                    "role": access.role,
                },
            )

    def test_api_organization_accesses_retrieve_authenticated_owner(self):
        """
        A user who is a direct owner of an organization should be allowed to retrieve the
        associated organization accesses
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "owner")])
        self.assertEqual(len(OrganizationAccess.ROLE_CHOICES), 3)

        for role, _name in OrganizationAccess.ROLE_CHOICES:
            access = factories.UserOrganizationAccessFactory(
                organization=organization, role=role
            )
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 200)
            content = response.json()
            self.assertTrue(content.pop("abilities")["get"])
            self.assertEqual(
                content,
                {
                    "id": str(access.id),
                    "role": access.role,
                    "user": str(access.user.id),
                },
            )

    def test_api_organization_accesses_retrieve_authenticated_owner_wrong_organization(
        self,
    ):
        """The organization in the url should match the targeted access."""
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization, other_organization = factories.OrganizationFactory.create_batch(
            2, users=[user]
        )
        access = factories.UserOrganizationAccessFactory(organization=organization)

        response = self.client.get(
            f"/api/v1.0/organizations/{other_organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 404)

    # Create

    def test_api_organization_accesses_create_anonymous(self):
        """Anonymous users should not be allowed to create organization accesses."""
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            {
                "user": str(user.id),
                "role": random.choice(["member", "administrator", "owner"]),
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        self.assertFalse(OrganizationAccess.objects.exists())

    def test_api_organization_accesses_create_authenticated(self):
        """Authenticated users should not be allowed to create organization accesses."""
        user, other_user = factories.UserFactory.create_batch(2)
        organization = factories.OrganizationFactory()

        jwt_token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            {
                "user": str(other_user.id),
                "role": random.choice(["member", "administrator", "owner"]),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "You must be administrator or owner of an organization to manage its accesses."
                )
            },
        )
        self.assertFalse(OrganizationAccess.objects.filter(user=other_user).exists())

    def test_api_organization_accesses_create_members(self):
        """
        A user who is a simple member in an organization should not be allowed to create
        organization accesses in this organization.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        organization = factories.OrganizationFactory(users=[(user, "member")])

        jwt_token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            {
                "user": str(other_user.id),
                "role": random.choice(["member", "administrator", "owner"]),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "You must be administrator or owner of an organization to manage its accesses."
                )
            },
        )
        self.assertFalse(OrganizationAccess.objects.filter(user=other_user).exists())

    def test_api_organization_accesses_create_administrators_except_owner(self):
        """
        A user who is administrator in an organization should be allowed to create organization
        accesses in this organization for roles other than owner (which is tested in the
        subsequent test).
        """
        user, other_user = factories.UserFactory.create_batch(2)
        organization = factories.OrganizationFactory(users=[(user, "administrator")])

        jwt_token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            {
                "user": str(other_user.id),
                "role": random.choice(["member", "administrator"]),
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(OrganizationAccess.objects.count(), 2)
        self.assertTrue(OrganizationAccess.objects.filter(user=other_user).exists())

    def test_api_organization_accesses_create_administrators_owner(self):
        """
        A user who is administrator in an organization should not be allowed to create
        organization accesses in this organization for the owner role.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        organization = factories.OrganizationFactory(users=[(user, "administrator")])

        jwt_token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/",
            {
                "user": str(other_user.id),
                "role": "owner",
            },
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(OrganizationAccess.objects.filter(user=other_user).exists())

    def test_api_organization_accesses_create_owner_all_roles(self):
        """
        A user who is owner in an organization should be allowed to create
        organization accesses in this organization for all roles.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(users=[(user, "owner")])

        jwt_token = self.get_user_token(user.username)

        for i, role in enumerate(["member", "administrator", "owner"]):
            other_user = factories.UserFactory()
            response = self.client.post(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/",
                {
                    "user": str(other_user.id),
                    "role": role,
                },
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(response.status_code, 201)
            self.assertEqual(OrganizationAccess.objects.count(), i + 2)
            self.assertTrue(OrganizationAccess.objects.filter(user=other_user).exists())

    # Update

    def test_api_organization_accesses_update_anonymous(self):
        """Anonymous users should not be allowed to update an organization access."""
        access = factories.UserOrganizationAccessFactory()
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory().id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_authenticated(self):
        """Authenticated users should not be allowed to update an organization access."""
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        access = factories.UserOrganizationAccessFactory()
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(users=[(user, "member")]).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_member(self):
        """
        A user who is a simple member in an organization should not be allowed to update
        a user access for this organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "member")])
        access = factories.UserOrganizationAccessFactory(organization=organization)
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(users=[(user, "member")]).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_administrator_except_owner(self):
        """
        A user who is an administrator in an organization should be allowed to update a user
        access for this organization, as long as s.he does not try to set the role to owner.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(["member", "administrator"]),
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
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
            updated_values = OrganizationAccessSerializer(instance=access).data
            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_administrator_from_owner(self):
        """
        A user who is an administrator in an organization, should not be allowed to update
        the user access of an owner for this organization.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=other_user, role="owner"
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_administrator_to_owner(self):
        """
        A user who is an administrator in an organization, should not be allowed to update
        the user access of another user when granting ownership.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization,
            user=other_user,
            role=random.choice(["member", "administrator"]),
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": "owner",
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
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
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_owner_except_owner(self):
        """
        A user who is an owner in an organization should be allowed to update
        a user access for this organization except for existing owner accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            new_data = {**old_values, field: value}
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
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
            updated_values = OrganizationAccessSerializer(instance=access).data

            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_owner_for_owners(self):
        """
        A user who is an owner in an organization should not be allowed to update
        an existing owner access for this organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }
        for field, value in new_values.items():
            response = self.client.put(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={**old_values, field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_update_owner_self(self):
        """
        A user who is an owner of an organization should be allowed to update
        her own user access provided there are other owners in the organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role="owner"
        )
        old_values = OrganizationAccessSerializer(instance=access).data
        new_role = random.choice(["member", "administrator"])

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            data={**old_values, "role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        access.refresh_from_db()
        self.assertEqual(access.role, "owner")

        # Add another owner and it should now work
        factories.UserOrganizationAccessFactory(organization=organization, role="owner")

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            data={**old_values, "role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        access.refresh_from_db()
        self.assertEqual(access.role, new_role)

    # Patch

    def test_api_organization_accesses_patch_anonymous(self):
        """Anonymous users should not be allowed to patch an organization access."""
        access = factories.UserOrganizationAccessFactory()
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory().id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_authenticated(self):
        """Authenticated users should not be allowed to patch an organization access."""
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        access = factories.UserOrganizationAccessFactory()
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(users=[(user, "member")]).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_member(self):
        """
        A user who is a simple member in an organization should not be allowed to update
        a user access for this organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "member")])
        access = factories.UserOrganizationAccessFactory(organization=organization)
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(users=[(user, "member")]).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_administrator_except_owner(self):
        """
        A user who is an administrator in an organization should be allowed to patch a user
        access for this organization, as long as s.he does not try to set the role to owner.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(["member", "administrator"]),
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
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
            updated_values = OrganizationAccessSerializer(instance=access).data
            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_administrator_from_owner(self):
        """
        A user who is an administrator in an organization, should not be allowed to patch
        the user access of an owner for this organization.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=other_user, role="owner"
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_administrator_to_owner(self):
        """
        A user who is an administrator in an organization, should not be allowed to patch
        the user access of another user when granting ownership.
        """
        user, other_user = factories.UserFactory.create_batch(2)
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization,
            user=other_user,
            role=random.choice(["member", "administrator"]),
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": "owner",
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            if field == "role":
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_owner_except_owner(self):
        """
        A user who is an owner in an organization should be allowed to patch
        a user access for this organization except for existing owner accesses.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }

        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
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
            updated_values = OrganizationAccessSerializer(instance=access).data

            if field == "role":
                self.assertEqual(
                    updated_values, {**old_values, "role": new_values["role"]}
                )
            else:
                self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_owner_for_owners(self):
        """
        A user who is an owner in an organization should not be allowed to patch
        an existing owner access for this organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )
        old_values = OrganizationAccessSerializer(instance=access).data

        new_values = {
            "id": uuid4(),
            "organization": factories.OrganizationFactory(
                users=[(user, "administrator")]
            ).id,
            "user": factories.UserFactory().id,
            "role": random.choice(OrganizationAccess.ROLE_CHOICES)[0],
        }
        for field, value in new_values.items():
            response = self.client.patch(
                f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
                data={field: value},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )
            self.assertEqual(response.status_code, 403)
            access.refresh_from_db()
            updated_values = OrganizationAccessSerializer(instance=access).data
            self.assertEqual(updated_values, old_values)

    def test_api_organization_accesses_patch_owner_self(self):
        """
        A user who is an owner of an organization should be allowed to patch
        her own user access provided there are other owners in the organization.
        """
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role="owner"
        )
        new_role = random.choice(["member", "administrator"])

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            data={"role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )
        self.assertEqual(response.status_code, 403)
        access.refresh_from_db()
        self.assertEqual(access.role, "owner")

        # Add another owner and it should now work
        factories.UserOrganizationAccessFactory(organization=organization, role="owner")

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            data={"role": new_role},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 200)
        access.refresh_from_db()
        self.assertEqual(access.role, new_role)

    # Delete

    def test_api_organization_accesses_delete_anonymous(self):
        """Anonymous users should not be allowed to destroy an organization access."""
        access = factories.UserOrganizationAccessFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(OrganizationAccess.objects.count(), 1)

    def test_api_organization_accesses_delete_authenticated(self):
        """
        Authenticated users should not be allowed to delete an organization access for an
        organization in which they are not administrator.
        """
        access = factories.UserOrganizationAccessFactory()
        user = factories.UserFactory()
        jwt_token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/organizations/{access.organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(OrganizationAccess.objects.count(), 1)

    def test_api_organization_accesses_delete_members(self):
        """
        Authenticated users should not be allowed to delete an organization access for an
        organization in which they are a simple member.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(users=[(user, "member")])
        access = factories.UserOrganizationAccessFactory(organization=organization)

        jwt_token = self.get_user_token(user.username)

        self.assertEqual(OrganizationAccess.objects.count(), 2)
        self.assertTrue(OrganizationAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(OrganizationAccess.objects.count(), 2)

    def test_api_organization_accesses_delete_administrators(self):
        """
        Users who are administrators in an organization should be allowed to delete a user access
        from the organization provided it is not ownership.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(users=[(user, "administrator")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )

        jwt_token = self.get_user_token(user.username)

        self.assertEqual(OrganizationAccess.objects.count(), 2)
        self.assertTrue(OrganizationAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(OrganizationAccess.objects.count(), 1)

    def test_api_organization_accesses_delete_owners_except_owners(self):
        """
        Users should be able to delete the organization access of another user
        for an organization of which they are owner except for owners.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=random.choice(["member", "administrator"])
        )

        jwt_token = self.get_user_token(user.username)

        self.assertEqual(OrganizationAccess.objects.count(), 2)
        self.assertTrue(OrganizationAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(OrganizationAccess.objects.count(), 1)

    def test_api_organization_accesses_delete_owners_for_owners(self):
        """
        Users should not be able to delete the organization access of another owner
        even for an organization in which they are direct owner.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory(users=[(user, "owner")])
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )

        jwt_token = self.get_user_token(user.username)

        self.assertEqual(OrganizationAccess.objects.count(), 2)
        self.assertTrue(OrganizationAccess.objects.filter(user=access.user).exists())
        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(OrganizationAccess.objects.count(), 2)

    def test_api_organization_accesses_delete_owners_last_owner(self):
        """
        It should not be possible to delete the last owner access from an organization
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role="owner"
        )

        jwt_token = self.get_user_token(user.username)

        self.assertEqual(OrganizationAccess.objects.count(), 1)
        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id!s}/accesses/{access.id!s}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(OrganizationAccess.objects.count(), 1)
