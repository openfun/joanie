"""
Test suite for organization access models
"""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
class OrganizationAccessModelsTestCase(BaseAPITestCase):
    """Test suite for the OrganizationAccess model."""

    def test_models_organization_access_organization_user_pair_unique(self):
        """Only one organization access object is allowed per organization/user pair."""
        access = factories.UserOrganizationAccessFactory()

        # Creating a second organization access for the same organization/user pair
        # should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.UserOrganizationAccessFactory(
                organization=access.organization, user=access.user
            )

        self.assertEqual(
            context.exception.messages[0],
            "Organization access with this Organization and User already exists.",
        )
        self.assertEqual(models.OrganizationAccess.objects.count(), 1)

    # get_abilities

    def test_models_organization_access_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        access = factories.UserOrganizationAccessFactory()
        abilities = access.get_abilities(AnonymousUser())

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": False,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        access = factories.UserOrganizationAccessFactory()
        abilities = access.get_abilities(factories.UserFactory())
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": False,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    # - for owner

    def test_models_organization_access_get_abilities_for_owner_of_self_allowed(self):
        """
        Check abilities of self access for the owner of a organization when there is more
        than one user left.
        """
        access = factories.UserOrganizationAccessFactory(role="owner")
        factories.UserOrganizationAccessFactory(
            organization=access.organization, role="owner"
        )  # another one
        abilities = access.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["administrator", "member"],
            },
        )

    def test_models_organization_access_get_abilities_for_owner_of_self_last(self):
        """
        Check abilities of self access for the owner of a organization when there is
        only one owner left.
        """
        access = factories.UserOrganizationAccessFactory(role="owner")
        abilities = access.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_for_owner_of_owner(self):
        """Check abilities of owner access for the owner of a organization."""
        access = factories.UserOrganizationAccessFactory(role="owner")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_for_owner_of_administrator(self):
        """Check abilities of administrator access for the owner of a organization."""
        access = factories.UserOrganizationAccessFactory(role="administrator")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["owner", "member"],
            },
        )

    def test_models_organization_access_get_abilities_for_owner_of_member(self):
        """Check abilities of member access for the owner of a organization."""
        access = factories.UserOrganizationAccessFactory(role="member")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["owner", "administrator"],
            },
        )

    # - for administrator

    def test_models_organization_access_get_abilities_for_administrator_of_owner(self):
        """Check abilities of owner access for the administator of a organization."""
        access = factories.UserOrganizationAccessFactory(role="owner")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_for_administrator_of_administrator(
        self,
    ):
        """Check abilities of administrator access for the administrator of a organization."""
        access = factories.UserOrganizationAccessFactory(role="administrator")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["member"],
            },
        )

    def test_models_organization_access_get_abilities_for_administrator_of_member(self):
        """Check abilities of member access for the administrator of a organization."""
        access = factories.UserOrganizationAccessFactory(role="member")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["administrator"],
            },
        )

    # - for member

    def test_models_organization_access_get_abilities_for_member_of_owner(self):
        """Check abilities of owner access for the member of a organization."""
        access = factories.UserOrganizationAccessFactory(role="owner")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="member"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_for_member_of_administrator(self):
        """Check abilities of administrator access for the member of a organization."""
        access = factories.UserOrganizationAccessFactory(role="administrator")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="member"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_for_member_of_member_user(self):
        """Check abilities of member access for the member of a organization."""
        access = factories.UserOrganizationAccessFactory(role="member")
        factories.UserOrganizationAccessFactory(
            organization=access.organization
        )  # another one
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="member"
        ).user

        with self.assertNumQueries(1):
            abilities = access.get_abilities(user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_organization_access_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        access = factories.UserOrganizationAccessFactory(role="member")
        user = factories.UserOrganizationAccessFactory(
            organization=access.organization, role="member"
        ).user
        access.user_role = "member"

        with self.assertNumQueries(0):
            abilities = access.get_abilities(user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )
