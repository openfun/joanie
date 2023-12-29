"""
Test suite for OrganizationAccess Admin API.
"""
import uuid
from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories


class OrganizationAccessAdminApiTest(TestCase):
    """
    Test suite for OrganizationAccess Admin API.
    """

    def test_admin_api_organization_accesses_request_anonymous(self):
        """
        Anonymous users should not be able to request organization accesses endpoint.
        """
        organization = factories.OrganizationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_organization_accesses_request_authenticated(self):
        """
        Authenticated users should not be able to request organization accesses endpoint.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        organization = factories.OrganizationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/"
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    def test_admin_api_organization_accesses_request_list(self):
        """
        Super admin user should not be able to list organization accesses.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/"
        )

        self.assertContains(
            response,
            'Method \\"GET\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_admin_api_organization_accesses_request_get(self):
        """
        Super admin user should not be able to retrieve an organization access.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization
        )
        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/"
        )

        self.assertContains(
            response,
            'Method \\"GET\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_admin_api_organization_accesses_request_create(self):
        """
        Super admin user should be able to create a course access.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            data={
                "user_id": str(user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(organization.accesses.count(), 1)
        organization_access = organization.accesses.first()
        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(organization_access.id),
                "role": "member",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.get_full_name(),
                },
            },
        )

    def test_admin_api_organization_accesses_request_create_with_unknown_user_id(self):
        """
        An 400 Bad request error should be raised if the user id is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory.build()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            data={
                "user_id": str(user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.json(), {"user_id": ["Resource does not exist."]})

    def test_admin_api_organization_accesses_request_create_with_unknown_course_id(
        self,
    ):
        """
        An 404 Not found error should be raised if the organization id is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory.build()
        user = factories.UserFactory()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            data={
                "user_id": str(user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertContains(response, "Not found.", status_code=HTTPStatus.NOT_FOUND)

    def test_admin_api_organization_accesses_request_create_with_invalid_role(self):
        """
        An 400 Bad request error should be raised if the role is not valid.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            data={
                "user_id": str(user.id),
                "role": "invalid_role",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"role": ['"invalid_role" is not a valid choice.']}
        )

    def test_admin_api_organization_accesses_request_update(self):
        """
        Super admin user should be able to update an organization access.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role=enums.MEMBER
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/",
            content_type="application/json",
            data={
                "user_id": str(user.id),
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(organization_access.id),
                "role": "owner",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.get_full_name(),
                },
            },
        )

    def test_admin_api_organization_accesses_request_update_with_unknown_course_id(
        self,
    ):
        """
        An 404 Not found error should be raised if the organization access id is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory.build()
        user = factories.UserFactory()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{uuid.uuid4()}/",
            data={
                "user_id": str(user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertContains(response, "Not found.", status_code=HTTPStatus.NOT_FOUND)

    def test_admin_api_organization_accesses_request_update_with_partial_payload(self):
        """
        An 400 Bad request error should be raised if a partial payload is provided.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role=enums.MEMBER
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/",
            content_type="application/json",
            data={
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        content = response.json()
        self.assertEqual(content, {"user_id": ["This field is required."]})

    def test_admin_api_organization_accesses_request_update_with_unknown_user(self):
        """
        An 400 Bad request error should be raised if the user id is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory.build()
        self.assertEqual(organization.accesses.count(), 0)

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            data={
                "user_id": str(user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.json(), {"user_id": ["Resource does not exist."]})

    def test_admin_api_organization_accesses_request_partial_update(self):
        """
        Super admin user should be able to partially update an organization access.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role=enums.MEMBER
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/",
            content_type="application/json",
            data={
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(organization_access.id),
                "role": "administrator",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.get_full_name(),
                },
            },
        )

    def test_admin_api_organization_accesses_request_delete(self):
        """
        Super admin user should be able to delete an organization access.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=user, role=enums.MEMBER
        )

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(organization.accesses.count(), 0)
