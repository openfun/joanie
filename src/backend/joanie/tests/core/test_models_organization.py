"""
Test suite for organization models
"""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationModelsTestCase(BaseAPITestCase):
    """Test suite for the Organization model."""

    def test_models_organization_fields_code_normalize(self):
        """The `code` field should be normalized to an ascii slug on save."""
        organization = factories.OrganizationFactory()

        organization.code = "Là&ça boô"
        organization.save()
        self.assertEqual(organization.code, "LACA-BOO")

    def test_models_organization_fields_code_unique(self):
        """The `code` field should be unique among organizations."""
        factories.OrganizationFactory(code="the-unique-code")

        # Creating a second organization with the same code should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.OrganizationFactory(code="the-unique-code")

        self.assertEqual(
            context.exception.messages[0], "Organization with this Code already exists."
        )
        self.assertEqual(
            models.Organization.objects.filter(code="THE-UNIQUE-CODE").count(), 1
        )

    # get_abilities

    def test_models_organization_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        organization = factories.OrganizationFactory()
        abilities = organization.get_abilities(AnonymousUser())

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
                "can_sign_contract": False,
            },
        )

    def test_models_organization_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        organization = factories.OrganizationFactory()
        abilities = organization.get_abilities(factories.UserFactory())
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
                "can_sign_contract": False,
            },
        )

    def test_models_organization_get_abilities_owner(self):
        """Check abilities returned for the owner of a organization."""
        access = factories.UserOrganizationAccessFactory(role="owner")
        abilities = access.organization.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
                "can_sign_contract": True,
            },
        )

    def test_models_organization_get_abilities_administrator(self):
        """Check abilities returned for the administrator of a organization."""
        access = factories.UserOrganizationAccessFactory(role="administrator")
        abilities = access.organization.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
                "can_sign_contract": False,
            },
        )

    def test_models_organization_get_abilities_member_user(self):
        """Check abilities returned for the member of a organization."""
        access = factories.UserOrganizationAccessFactory(role="member")

        with self.assertNumQueries(1):
            abilities = access.organization.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
                "can_sign_contract": False,
            },
        )

    def test_models_organization_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        access = factories.UserOrganizationAccessFactory(role="member")
        access.organization.user_role = "member"

        with self.assertNumQueries(0):
            abilities = access.organization.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
                "can_sign_contract": False,
            },
        )
