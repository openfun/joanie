"""
Test suite for accounts models
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from joanie.core import factories


class AddressTestCase(TestCase):
    """Test suite for Address model"""

    def test_model_address_main_is_unique(self):
        """
        Address model allows only one main address per user. Try to save a
        second main address, the existing main address should be demoted.
        """
        # first declare a main address for a user
        address1 = factories.AddressFactory(is_main=True, is_reusable=True)
        user = address1.owner
        self.assertTrue(user.addresses.get().is_main)

        # then declare an other main address for a user
        address2 = factories.AddressFactory(is_main=True, owner=user, is_reusable=True)

        # so the former main address is no longer the main address
        address1.refresh_from_db()
        self.assertFalse(address1.is_main)
        self.assertTrue(address2.is_main)

    def test_model_address_first_reusable_address_is_main_by_default(self):
        """
        The first reusable user address created is set as main by default
        """
        owner = factories.UserFactory()
        first_address, second_address = factories.AddressFactory.create_batch(
            2, owner=owner, is_main=False, is_reusable=True
        )

        self.assertTrue(first_address.is_main)
        self.assertFalse(second_address.is_main)

    def test_model_address_not_reusable_address_is_not_main_by_default(self):
        """
        The first non-reusable user address created is not set as main by default
        """
        owner = factories.UserFactory()
        first_address = factories.AddressFactory.create(
            owner=owner, is_main=False, is_reusable=False
        )

        self.assertEqual(first_address.is_main, False)

    def test_model_address_forbid_update_as_main_when_there_is_another(self):
        """
        It should raise an error if user tries to update an address as main even
        though there is already a main address
        """

        user = factories.UserFactory()
        factories.AddressFactory(owner=user, is_main=True, is_reusable=True)
        address = factories.AddressFactory(owner=user, is_main=False, is_reusable=True)

        # Try to update address as main is forbidden
        with self.assertRaises(IntegrityError):
            user.addresses.filter(pk=address.pk).update(is_main=True)

    def test_model_address_forbid_demote_main_address_directly(self):
        """
        It should raise an error if user tries to demote its main address
        """
        user = factories.UserFactory()
        address = factories.AddressFactory(owner=user, is_main=True, is_reusable=True)

        # Try to demote the main address
        with self.assertRaises(ValidationError):
            address.is_main = False
            address.save()

    def test_model_address_full_name_property(self):
        """
        address.full_name should concatenate first_name and last_name
        """
        address = factories.AddressFactory()
        self.assertEqual(address.full_name, f"{address.first_name} {address.last_name}")

    def test_model_address_full_address_property(self):
        """
        address.full_address should return
        address formatted into a human readable format
        """
        address = factories.AddressFactory()

        self.assertEqual(
            address.full_address,
            f"{address.address}\n{address.postcode} {address.city}\n{address.country.name}",
        )

    def test_model_address_main_address_must_be_reusable(self):
        """
        If an address is set as main, it must be reusable
        """

        with self.assertRaises(ValidationError) as context:
            factories.AddressFactory(is_main=True, is_reusable=False)

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A main address must be reusable
        address = factories.AddressFactory(is_main=True, is_reusable=True)

        # Then cannot be marked as not reusable
        address.is_reusable = False

        with self.assertRaises(ValidationError) as context:
            address.save()

        self.assertEqual(
            context.exception.messages[0], "Main address must be reusable."
        )

        # A not main address can be reusable or not
        factories.AddressFactory(is_main=False, is_reusable=False)
        factories.AddressFactory(is_main=False, is_reusable=True)
