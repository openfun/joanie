"""
Test suite for organization models
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core import factories, models


class OrganizationModelsTestCase(TestCase):
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
