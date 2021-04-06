"""
Test suite for accounts models
"""

from django.test import TestCase

from joanie.core import factories


class AddressTestCase(TestCase):
    """Test suite for Address model"""

    def test_create_address_main(self):
        """Manage main status on Address object created"""
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
