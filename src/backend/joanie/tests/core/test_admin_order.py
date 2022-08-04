"""
Test suite for orders admin pages
"""

from unittest import mock

from django.urls import reverse

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrderAdminTestCase(BaseAPITestCase):
    """Test suite for admin to manipulate orders."""

    @mock.patch.object(models.Order, "cancel")
    def test_admin_order_action_cancel(self, mock_cancel):
        """
        Order admin should display an action to cancel an order which call
        order.cancel method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        order = factories.OrderFactory()
        self.client.login(username=user.username, password="password")
        order_changelist_page = reverse("admin:core_order_changelist")
        response = self.client.get(order_changelist_page)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancel selected orders")

        # - Trigger "cancel" action
        self.client.post(
            order_changelist_page, {"action": "cancel", "_selected_action": order.pk}
        )
        self.assertEqual(response.status_code, 200)
        mock_cancel.assert_called_once_with()
