"""Test suite for utils organization methods"""

from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.utils.organization import get_least_active_organization


class UtilsOrganizationTestCase(TestCase):
    """Test suite for utils organization methods"""

    def setUp(self):
        """Set up the test case"""
        super().setUp()
        self.organization_1, self.organization_2 = (
            factories.OrganizationFactory.create_batch(2)
        )
        self.offering = factories.OfferingFactory(
            organizations=[self.organization_1, self.organization_2]
        )
        self.course = self.offering.course
        self.product = self.offering.product

    def test_utils_organization_get_least_active_organization_no_orders(self):
        """
        With no orders, a random organization is returned.
        """
        selected_organization = get_least_active_organization(self.product, self.course)

        # the first selected organization is random
        self.assertIn(selected_organization, [self.organization_1, self.organization_2])

        # Add a completed order to the selected organization
        factories.OrderFactory(
            product=self.product,
            course=self.course,
            organization=selected_organization,
            state=enums.ORDER_STATE_COMPLETED,
        )

        # The next selected organization should be the other one
        next_selected_organization = get_least_active_organization(
            self.product, self.course
        )
        self.assertEqual(type(next_selected_organization), type(selected_organization))
        self.assertNotEqual(next_selected_organization, selected_organization)

    def test_utils_organization_get_least_active_organization_is_author(self):
        """
        With no order, and the first organization is the author, it is returned.
        """
        self.organization_1.courses.add(self.course)

        selected_organization = get_least_active_organization(self.product, self.course)

        self.assertEqual(selected_organization, self.organization_1)

    def test_utils_organization_get_least_active_organization_all_states(self):
        """
        With one order to the first organization, the second organization is returned.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(f"{state} order to the first organization", state=state):
                self.setUp()
                factories.OrderFactory(
                    product=self.product,
                    course=self.course,
                    organization=self.organization_1,
                    state=state,
                )
                # Add the course to the first organization to avoid randomness
                self.organization_1.courses.add(self.course)
                self.assertEqual(self.organization_1.courses.count(), 1)

                selected_organization = get_least_active_organization(
                    self.product, self.course
                )
                if state in [
                    enums.ORDER_STATE_DRAFT,
                    enums.ORDER_STATE_ASSIGNED,
                    enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                    enums.ORDER_STATE_TO_SIGN,
                    enums.ORDER_STATE_SIGNING,
                    enums.ORDER_STATE_CANCELED,
                    enums.ORDER_STATE_REFUNDING,
                    enums.ORDER_STATE_REFUNDED,
                ]:
                    self.assertEqual(selected_organization, self.organization_1)
                else:
                    self.assertEqual(selected_organization, self.organization_2)
