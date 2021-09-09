"""
Test suite for accounts models
"""

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
        address1 = factories.AddressFactory(main=True)
        user = address1.owner
        self.assertTrue(user.addresses.get().main)

        # then declare an other main address for a user
        address2 = factories.AddressFactory(main=True, owner=user)

        # so the former main address is no longer the main address
        address1.refresh_from_db()
        self.assertFalse(address1.main)
        self.assertTrue(address2.main)

    def test_model_address_forbid_update_as_main_when_there_is_another(self):
        """
        It should raise an error if user tries to update an address as main even
        though there is already a main address
        """

        user = factories.UserFactory()
        factories.AddressFactory(owner=user, main=True)
        address = factories.AddressFactory(owner=user, main=False)

        # Try to update address as main is forbidden
        with self.assertRaises(IntegrityError):
            user.addresses.filter(pk=address.pk).update(main=True)
