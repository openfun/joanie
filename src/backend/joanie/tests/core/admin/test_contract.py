"""Test suite for the admin django contract app"""

from http import HTTPStatus

from django.urls import reverse

from joanie.core import enums
from joanie.core.factories import BatchOrderFactory, OrderGeneratorFactory, UserFactory
from joanie.tests.base import BaseAPITestCase


class ContractAdminTestCase(BaseAPITestCase):
    """Test suite for the admin django contract app"""

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=self.admin_user.username, password="password")
        # Create contracts related to orders
        OrderGeneratorFactory.create_batch(3, state=enums.ORDER_STATE_SIGNING)
        # Create contracts related to batch orders
        BatchOrderFactory.create_batch(3, state=enums.BATCH_ORDER_STATE_SIGNING)

    def test_admin_contract_list_view(self):
        """Test for admin contract list view return status code 200"""
        contract_url = reverse("admin:core_contract_changelist")

        response = self.client.get(contract_url)

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
