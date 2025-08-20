"""
Test suite for accounts models for users and organizations.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings

from joanie.core import factories, models


# pylint: disable=too-many-public-methods
@override_settings(LANGUAGE_CODE="en-us")
class AddressModelTestCase(TestCase):
    """Test suite for Address model when related to a user, and then, to an organization."""

    def test_models_address_full_name_property(self):
        """
        address.full_name should concatenate first_name and last_name.
        """
        address = factories.UserAddressFactory()

        self.assertEqual(address.full_name, f"{address.first_name} {address.last_name}")

    def test_models_address_full_address_property(self):
        """
        address.full_address should return address formatted into a human readable format.
        """
        address = factories.UserAddressFactory()

        self.assertEqual(
            address.full_address,
            f"{address.address}\n{address.postcode} {address.city}\n{address.country.name}",
        )

    def test_models_address_create_without_an_organization_and_a_user(
        self,
    ):
        """
        When we attempt to create an object without an organization and a user, it should raise an
        error.
        """
        with self.assertRaises(ValidationError) as context:
            models.Address.objects.create(
                owner=None,
                organization=None,
                title="Home",
                address="1 rue de l'exemple",
                postcode="75000",
                city="Paris",
                country="FR",
                first_name="firstname",
                last_name="lastname",
                is_main=False,
                is_reusable=False,
            )

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Either owner or organization must be set.']}",
        )

    def test_models_address_create_with_an_organization_and_a_user(
        self,
    ):
        """
        When we attempt to create an object with an organization and a user at the same time,
        it should raise an error.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()

        with self.assertRaises(ValidationError) as context:
            models.Address.objects.create(
                owner=user,
                organization=organization,
                title="Office",
                address="1 rue de l'exemple",
                postcode="75000",
                city="Paris",
                country="FR",
                first_name="firstname",
                last_name="lastname",
                is_main=False,
                is_reusable=False,
            )

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Either owner or organization must be set.']}",
        )

    def test_models_address_add_relation_organization_post_creation_the_address_of_an_owner(
        self,
    ):
        """
        It must raise an error if we set an organization relation on an existing address object
        that is already attached to a user.
        """
        user = factories.UserFactory()
        address = factories.UserAddressFactory(
            owner=user, is_reusable=True, is_main=True
        )
        organization = factories.OrganizationFactory()

        # Try to add the organization on the address object
        address.organization = organization

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Either owner or organization must be set.']}",
        )

    def test_models_address_add_relation_owner_post_create_the_address_of_an_organization(
        self,
    ):
        """
        It must raise an error if we set a user relation on an existing address object that is
        already attached to an organization.
        """
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(
            organization=organization, is_reusable=True, is_main=True
        )
        user = factories.UserFactory()

        # Try to add the user on the address object
        address.owner = user

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Either owner or organization must be set.']}",
        )

    def test_models_address_user_main_is_unique(self):
        """
        Address model allows only one main address per user. Try to save a second main address,
        the existing main address should be demoted.
        """
        # first declare a main address for a user
        address1 = factories.UserAddressFactory(is_main=True, is_reusable=True)
        user = address1.owner
        self.assertTrue(user.addresses.get().is_main)

        # then declare an other main address for a user
        address2 = factories.UserAddressFactory(
            is_main=True, owner=user, is_reusable=True
        )

        # so the former main address is no longer the main address
        address1.refresh_from_db()
        self.assertFalse(address1.is_main)
        self.assertTrue(address2.is_main)

    def test_models_address_organization_main_is_unique(self):
        """
        Address model allows only one main address per organization. Try to save a second main
        address, the existing main address should be demoted.
        """
        # first declare a main address for an organization
        address1 = factories.OrganizationAddressFactory(is_main=True, is_reusable=True)
        organization = address1.organization
        self.assertTrue(organization.addresses.get().is_main)

        # then declare another main address for the organization
        address2 = factories.OrganizationAddressFactory(
            organization=organization, is_main=True, is_reusable=True
        )

        # so the former main address is no longer the main address
        address1.refresh_from_db()
        self.assertFalse(address1.is_main)
        self.assertTrue(address2.is_main)

    def test_models_address_user_first_reusable_address_is_main_by_default(self):
        """
        The first reusable user address created is set as main by default.
        """
        owner = factories.UserFactory()
        first_address, second_address = factories.UserAddressFactory.create_batch(
            2, owner=owner, is_main=False, is_reusable=True
        )

        self.assertTrue(first_address.is_main)
        self.assertFalse(second_address.is_main)

    def test_models_address_organization_first_reusable_address_is_main_by_default(
        self,
    ):
        """
        The first reusable organization address created is set as main by default.
        """
        organization = factories.OrganizationFactory()
        (
            first_address,
            second_address,
        ) = factories.OrganizationAddressFactory.create_batch(
            2, organization=organization, is_main=False, is_reusable=True
        )

        self.assertTrue(first_address.is_main)
        self.assertFalse(second_address.is_main)

    def test_models_address_user_not_reusable_address_is_not_main_by_default(self):
        """
        The first non-reusable user address created is not set as main by default.
        """
        owner = factories.UserFactory()
        first_address = factories.UserAddressFactory.create(
            owner=owner, is_main=False, is_reusable=False
        )

        self.assertEqual(first_address.is_main, False)

    def test_models_address_organization_not_reusable_address_is_not_main_by_default(
        self,
    ):
        """
        The first non-reusable organization address created is not set as main by default.
        """
        organization = factories.OrganizationFactory()
        first_address = factories.OrganizationAddressFactory.create(
            organization=organization, is_main=False, is_reusable=False
        )

        self.assertEqual(first_address.is_main, False)

    def test_models_address_user_forbid_update_as_main_when_there_is_another(self):
        """
        It should raise an error if a user tries to update an address as main even
        though there is already a main address.
        """

        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user, is_main=True, is_reusable=True)
        address = factories.UserAddressFactory(
            owner=user, is_main=False, is_reusable=True
        )

        # Try to update address as main is forbidden
        with self.assertRaises(IntegrityError):
            user.addresses.filter(pk=address.pk).update(is_main=True)

    def test_models_address_organization_forbid_update_as_main_when_there_is_another(
        self,
    ):
        """
        It should raise an error if an organization tries to update an address as main
        even though there is already a main address.
        """

        organization = factories.OrganizationFactory()
        factories.OrganizationAddressFactory(
            organization=organization, is_main=True, is_reusable=True
        )
        address = factories.OrganizationAddressFactory(
            organization=organization, is_main=False, is_reusable=True
        )

        # Try to update address as main is forbidden
        with self.assertRaises(IntegrityError):
            organization.addresses.filter(pk=address.pk).update(is_main=True)

    def test_models_address_user_forbid_demote_main_address_directly(self):
        """
        It should raise an error if a user tries to demote its main address.
        """
        user = factories.UserFactory()
        address = factories.UserAddressFactory(
            owner=user, is_main=True, is_reusable=True
        )

        # Try to demote the main address
        address.is_main = False

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Demote a main address is forbidden']}",
        )

    def test_models_address_organization_forbid_demote_main_address_directly(self):
        """
        It should raise an error if an organization tries to demote its main address.
        """
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(
            organization=organization, is_main=True, is_reusable=True
        )

        # Try to demote the main address
        address.is_main = False

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Demote a main address is forbidden']}",
        )

    def test_models_address_user_main_address_must_be_reusable(self):
        """
        If an address is set as main for a user, it must be reusable.
        """

        with self.assertRaises(ValidationError) as context:
            factories.UserAddressFactory(is_main=True, is_reusable=False)

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A main address must be reusable
        address = factories.UserAddressFactory(is_main=True, is_reusable=True)

        # Then cannot be marked as not reusable
        address.is_reusable = False

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A not main address can be reusable or not
        factories.UserAddressFactory(is_main=False, is_reusable=False)
        factories.UserAddressFactory(is_main=False, is_reusable=True)

    def test_models_address_organization_main_address_must_be_reusable(self):
        """
        If an address is set as main for an organization, it must be reusable.
        """

        with self.assertRaises(ValidationError) as context:
            factories.OrganizationAddressFactory(is_main=True, is_reusable=False)

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A main address must be reusable
        address = factories.OrganizationAddressFactory(is_main=True, is_reusable=True)

        # Then cannot be marked as not reusable
        address.is_reusable = False

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A not main address can be reusable or not
        factories.OrganizationAddressFactory(is_main=False, is_reusable=False)
        factories.OrganizationAddressFactory(is_main=False, is_reusable=True)

    def test_models_address_unique_main_address_per_organization(self):
        """
        We should not be able to create a second main address for an organizaiton if there
        is already a main address that is reusable. An organization cannot have 2 main addresses
        at the same time, it should raise an error.
        """
        organization = factories.OrganizationFactory()
        factories.OrganizationAddressFactory(
            organization=organization, is_main=False, is_reusable=True
        )

        # Try to create another is_main address for the organization
        with self.assertRaises(ValidationError) as context:
            factories.OrganizationAddressFactory(
                organization=organization, is_main=True, is_reusable=False
            )

        self.assertEqual(
            str(context.exception.messages[0]),
            "Constraint “unique_main_address_per_organization” is violated.",
        )

    def test_models_address_unique_main_address_per_user(self):
        """
        We should not be able to create a second main address for a user if there
        is already a main address that is reusable. A user cannot have 2 main addresses at the same
        time, it should raise an error.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user, is_main=True, is_reusable=True)

        # Try to create another is_main address for the user
        with self.assertRaises(ValidationError) as context:
            factories.UserAddressFactory(owner=user, is_main=True, is_reusable=False)

        self.assertEqual(
            str(context.exception.messages[0]),
            "Constraint “unique_main_address_per_user” is violated.",
        )

    def test_models_address_create_two_address_with_two_users_and_both_none_organization(
        self,
    ):
        """
        We should be able to create two addresses, for two different owners (users) where
        (organization) is None. We make sure that there is no constraint having two addresses
        where 'organization' is None.
        """
        [user_1, user_2] = factories.UserFactory.create_batch(2)
        address_1 = factories.UserAddressFactory(
            owner=user_1, organization=None, is_main=True, is_reusable=True
        )
        address_2 = factories.UserAddressFactory(
            owner=user_2, organization=None, is_main=True, is_reusable=True
        )
        self.assertEqual(address_1.is_main, True)
        self.assertEqual(address_2.is_main, True)

    def test_models_address_create_two_address_with_two_organizations_and_both_none_owner(
        self,
    ):
        """
        We should be able to create two addresses, for two different organizations where
        owner (user) is None. We make sure that there is no constraint having two addresses
        where 'owner' is None.
        """
        organization_1, organization_2 = factories.OrganizationFactory.create_batch(2)
        address_1 = factories.OrganizationAddressFactory(
            organization=organization_1, owner=None, is_main=True, is_reusable=True
        )
        address_2 = factories.OrganizationAddressFactory(
            organization=organization_2, owner=None, is_main=True, is_reusable=True
        )
        self.assertEqual(address_1.is_main, True)
        self.assertEqual(address_2.is_main, True)

    def test_models_address_unique_constraint_one_address_per_user(self):
        """
        Check the unique constraint `unique_address_per_user`
        that protects to add in the database 2 identical addresses for a user.
        """
        owner = factories.UserFactory()
        factories.AddressFactory(
            owner=owner,
            address="1 rue de l'exemple",
            postcode="75000",
            city="Paris",
            country="FR",
            first_name="firstname",
            last_name="lastname",
        )

        with self.assertRaises(ValidationError) as context:
            factories.AddressFactory(
                owner=owner,
                address="1 rue de l'exemple",
                postcode="75000",
                city="Paris",
                country="FR",
                first_name="firstname",
                last_name="lastname",
            )

        self.assertEqual(
            str(context.exception.messages[0]),
            "Address with this Owner, Address, Postcode, City, "
            "Country, First name and Last name already exists.",
        )

    def test_models_address_unique_constraint_one_address_per_organization(self):
        """
        Check the unique constraint `unique_address_per_organization`
        that protects to add in the database 2 identical addresses for an organization.
        """
        organization = factories.OrganizationFactory()
        factories.AddressFactory(
            organization=organization,
            address="2 rue de l'exemple",
            postcode="75000",
            city="Paris",
            country="FR",
            first_name="firstname",
            last_name="lastname",
        )

        with self.assertRaises(ValidationError) as context:
            factories.AddressFactory(
                organization=organization,
                address="2 rue de l'exemple",
                postcode="75000",
                city="Paris",
                country="FR",
                first_name="firstname",
                last_name="lastname",
            )

        self.assertEqual(
            str(context.exception.messages[0]),
            "Address with this Organization, Address, Postcode, City, "
            "Country, First name and Last name already exists.",
        )
