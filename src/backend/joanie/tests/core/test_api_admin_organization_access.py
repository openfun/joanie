"""
Test suite for OrganizationAccess Admin API.
"""

import uuid
from http import HTTPStatus
from unittest import mock

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
                    "email": user.email,
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

        self.assertContains(
            response,
            "No Organization matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

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
                    "email": user.email,
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

        self.assertContains(
            response,
            "No OrganizationAccess matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

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
                    "email": user.email,
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

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_create_triggers_update_signatories_for_organization(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin creates a new organization access with the 'owner' role,
        it should trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            content_type="application/json",
            data={
                "user_id": str(user.id),
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(organization.accesses.count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        member_user = factories.UserFactory()
        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            content_type="application/json",
            data={
                "user_id": str(member_user.id),
                "role": enums.MEMBER,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(organization.accesses.count(), 2)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertFalse(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.reset_mock()

        admin_user = factories.UserFactory()
        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/",
            content_type="application/json",
            data={
                "user_id": str(admin_user.id),
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(organization.accesses.count(), 3)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertFalse(mock_update_organization_signatories.delay.called)

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_update_role_to_owner_trigger_update_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin updates an existing organization access to the 'owner' role,
        it should trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.MEMBER
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/",
            content_type="application/json",
            data={
                "user_id": str(organization_access.user.id),
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 1)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        organization_access_2 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.ADMIN
        )
        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access_2.id}/",
            content_type="application/json",
            data={
                "user_id": str(organization_access_2.user.id),
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 2)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 2)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_update_role_from_owner_trigger_update_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin updates an existing organization access from the 'owner' role
        to 'member' or 'admin', it should trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_1 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_2 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_1.id}/",
            content_type="application/json",
            data={
                "user_id": str(access_1.user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 3)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 2)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_2.id}/",
            content_type="application/json",
            data={
                "user_id": str(access_2.user.id),
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 3)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertEqual(organization.accesses.filter(role=enums.ADMIN).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_role_member_or_admin_should_not_trigger_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin updates an existing organization access where the role is not 'owner'
        at its origin, it should not trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.ADMIN
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "user_id": str(access.user.id),
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 1)
        self.assertFalse(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "user_id": str(access.user.id),
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(mock_update_organization_signatories.delay.called)

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_partially_update_to_owner_trigger_update_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin partially updates an existing organization access to the 'owner' role,
        it should trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        organization_access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.MEMBER
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access.id}/",
            content_type="application/json",
            data={
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 1)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        organization_access_2 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.ADMIN
        )
        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{organization_access_2.id}/",
            content_type="application/json",
            data={
                "role": enums.OWNER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 2)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 2)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_partial_update_from_owner_trigger_update_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin partially updates an existing organization access from the
        'owner' role to 'member' or 'admin', it should trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_1 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_2 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_1.id}/",
            content_type="application/json",
            data={
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 3)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 2)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_2.id}/",
            content_type="application/json",
            data={
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.count(), 3)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertEqual(organization.accesses.filter(role=enums.ADMIN).count(), 1)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_partial_member_or_admin_not_trigger_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin partially updates an existing organization access where
        the role is not 'owner' at its origin, it should not trigger the update of signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.ADMIN
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "role": enums.MEMBER,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 1)
        self.assertFalse(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "role": enums.ADMIN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(mock_update_organization_signatories.delay.called)

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_delete_organization_access_trigger_update_signatories(
        self, mock_update_organization_signatories
    ):
        """
        When the super admin deletes an existing organization access where the role is 'owner',
        it should trigger the update of signatories. The update should happen only when the role
        was 'owner'.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        # Always keep 1 owner access for the organization
        factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_1 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )
        access_2 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.MEMBER
        )
        access_3 = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.ADMIN
        )

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_1.id}/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(organization.accesses.filter(role=enums.OWNER).count(), 1)
        self.assertTrue(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.assert_called_with(
            organization_id=organization.id
        )
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_2.id}/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(organization.accesses.filter(role=enums.MEMBER).count(), 0)
        self.assertFalse(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.reset_mock()

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access_3.id}/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(organization.accesses.filter(role=enums.ADMIN).count(), 0)
        self.assertFalse(mock_update_organization_signatories.delay.called)
        mock_update_organization_signatories.delay.reset_mock()

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_update_owner_with_wrong_role_should_not_update(
        self, mock_update_organization_signatories
    ):
        """
        When we request to update an organization access with a valid user and an invalid role,
        it should be blocked and not trigger the update of contract signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "user_id": str(access.user.id),
                "role": "invalid_fake_role",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"role": ['"invalid_fake_role" is not a valid choice.']}
        )
        self.assertFalse(mock_update_organization_signatories.delay.called)

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_partial_owner_with_wrong_role_should_not_update(
        self, mock_update_organization_signatories
    ):
        """
        When we request to partially update an organization access with an invalid role, it should
        be blocked and not trigger the update of contract signatories.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
            data={
                "role": "invalid_fake_role",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"role": ['"invalid_fake_role" is not a valid choice.']}
        )
        self.assertFalse(mock_update_organization_signatories.delay.called)

    @mock.patch("joanie.core.api.admin.update_organization_signatories_contracts_task")
    def test_admin_api_organization_accesses_delete_last_organization_owner_should_not_update(
        self, mock_update_organization_signatories
    ):
        """
        When we request to delete the last organization access with the 'owner' role, it should not
        be allowed and it should not call the task to update the signatories for contracts.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        access = factories.UserOrganizationAccessFactory(
            organization=organization, user=factories.UserFactory(), role=enums.OWNER
        )

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{access.id}/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            response.json(),
            {"detail": "An organization should keep at least one owner."},
        )
        self.assertFalse(mock_update_organization_signatories.delay.called)
