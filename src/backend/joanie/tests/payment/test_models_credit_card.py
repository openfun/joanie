"""Test suite for the `CreditCard` Manager."""

from unittest import mock

from django.core.exceptions import FieldError, ValidationError

from joanie.core import enums
from joanie.core.factories import OrderFactory, UserFactory
from joanie.core.models import Order
from joanie.payment.exceptions import PaymentProviderAPIException
from joanie.payment.factories import CreditCardFactory
from joanie.payment.models import CreditCard
from joanie.tests.base import LoggingTestCase


class CreditCardModelTestCase(LoggingTestCase):
    """
    Test case for the CreditCard Manager.
    """

    def test_models_credit_card_get_card_for_owner(self):
        """
        If the `pk` and the `owner.username` matches an existing credit card, the manager
        method `get_card_for_owner` of the `CreditCard` model should return the object.
        When it does not match any objects in the database, it should raise the error
        CreditCard.DoesNotExist.
        """
        user = UserFactory()
        credit_card = CreditCardFactory(owners=[user])
        another_user = UserFactory()
        another_credit_card = CreditCardFactory(owners=[another_user])

        credit_card = CreditCard.objects.get_card_for_owner(
            pk=credit_card.pk, username=user.username
        )

        self.assertIn(user, credit_card.owners.all())

        with self.assertRaises(CreditCard.DoesNotExist) as context:
            CreditCard.objects.get_card_for_owner(
                pk=another_credit_card.id,
                username=user.username,
            )

        self.assertEqual(
            str(context.exception), "CreditCard matching query does not exist."
        )

    def test_models_credit_card_requires_a_payment_provider_value(self):
        """
        When creating a credit card object, it must have a value for the field `payment_provider`.
        If the field does not have a value, it will raise a `ValidationError`.
        """

        with self.assertRaises(ValidationError) as context:
            CreditCardFactory(payment_provider=None)

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Payment provider field cannot be None.']}",
        )

        with self.assertRaises(ValidationError) as context:
            CreditCardFactory(payment_provider="")

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Payment provider field cannot be None.']}",
        )

    def test_models_credit_card_get_cards_for_owner(self):
        """
        The manager method `get_cards_for_owner` should retrieve the credit cards of a given
        user by passing their username to the method parameter.
        Only the cards with the active payment backend should be retrieved.
        """
        owner = UserFactory()
        CreditCardFactory.create_batch(3, owners=[owner])
        CreditCardFactory(owners=[owner], payment_provider="lyra")
        another_owner = UserFactory()
        CreditCardFactory(owners=[another_owner])

        results = CreditCard.objects.get_cards_for_owner(username=owner.username)

        # There should be 4 existing cards for the owner overall
        self.assertEqual(CreditCard.objects.filter(owners=owner).count(), 4)
        # But only 3 cards should be retrieve because of the active payment backend
        self.assertEqual(results.count(), 3)
        for card in results:
            self.assertEqual(card.payment_provider, "dummy")
            self.assertIn(owner, card.owners.all())

    @mock.patch("joanie.payment.backends.dummy.DummyPaymentBackend.delete_credit_card")
    def test_models_credit_card_delete_on_payment_provider(
        self, mock_delete_credit_card
    ):
        """
        When a credit card is deleted from our database, it should also be
        deleted from the payment provider.
        """
        credit_card = CreditCardFactory()

        credit_card.delete()
        mock_delete_credit_card.assert_called_once_with(credit_card)

        self.assertEqual(CreditCard.objects.count(), 0)

    @mock.patch("joanie.payment.backends.dummy.DummyPaymentBackend.delete_credit_card")
    def test_models_credit_card_delete_on_payment_provider_error(
        self, mock_delete_credit_card
    ):
        """
        When a credit card is deleted from our database, it should also be
        deleted from the payment provider. If the request to the payment provider
        fails, it should raise an exception but should prevent the resource deletion.
        """
        mock_delete_credit_card.side_effect = PaymentProviderAPIException(
            "Token not found"
        )
        credit_card = CreditCardFactory()

        with self.assertLogs() as logger:
            credit_card.delete()

        mock_delete_credit_card.assert_called_once_with(credit_card)
        self.assertEqual(CreditCard.objects.count(), 0)

        expected_logs = [
            (
                "ERROR",
                "An error occurred while deleting a credit card token from payment provider.",
                {"paymentMethodToken": str},
            ),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    def test_models_credit_card_get_cards_when_credit_card_has_many_owners(self):
        """
        When the credit card is shared among users, the manager method `get_cards_for_owner`
        should retrieve the available credit cards of a given user by passing their username
        to the method parameter. Plus, only the cards with the active payment
        backend should be retrieved.
        """
        # Those users will share some credit cards
        owner_1 = UserFactory()
        owner_2 = UserFactory()
        owner_3 = UserFactory()
        # We create 4 cards with the active payment backend
        CreditCardFactory.create_batch(4, owners=[owner_1, owner_2])
        # Create another share credit card with owner_1 and owner_3
        CreditCardFactory(owners=[owner_1, owner_3])
        # We create another card from another payment backend that should not be in results
        CreditCardFactory(owners=[owner_1, owner_2], payment_provider="lyra")

        # Create another credit card for another user
        another_user = UserFactory()
        CreditCardFactory(owners=[another_user])

        results = CreditCard.objects.get_cards_for_owner(username=owner_1.username)

        # There should be 6 cards overall with the active payment provider ('dummy')
        self.assertEqual(CreditCard.objects.filter(owners=owner_1).count(), 6)
        # There should be 5 existing cards for the owner_1
        self.assertEqual(results.count(), 5)
        for card in results:
            self.assertEqual(card.payment_provider, "dummy")
            self.assertIn(owner_1, card.owners.all())

        results = CreditCard.objects.get_cards_for_owner(username=owner_2.username)

        # There should be 5 existing cards for the owner_2 overall
        self.assertEqual(CreditCard.objects.filter(owners=owner_2).count(), 5)
        # There should be only 4 cards with the active payment provider ('dummy')
        # because the last one was provided by another payment provider ('lyra')
        self.assertEqual(results.count(), 4)
        for card in results:
            self.assertEqual(card.payment_provider, "dummy")
            self.assertIn(owner_2, card.owners.all())
            self.assertIn(owner_1, card.owners.all())

        results = CreditCard.objects.get_cards_for_owner(username=owner_3.username)

        self.assertEqual(CreditCard.objects.filter(owners=owner_3).count(), 1)
        self.assertEqual(results.count(), 1)
        for card in results:
            self.assertEqual(card.payment_provider, "dummy")
            self.assertIn(owner_3, card.owners.all())
            self.assertIn(owner_1, card.owners.all())

    def test_models_credit_card_get_card_for_owner_when_credit_card_has_multiple_owner(
        self,
    ):
        """
        If the `pk` and the `owner.username` matches an existing credit card even if it is
        shared between users, the manager method `get_card_for_owner` of the `CreditCard`
        model should return the object.
        """
        owner_1 = UserFactory()
        owner_2 = UserFactory()
        credit_card = CreditCardFactory(owners=[owner_1, owner_2])
        another_user = UserFactory()
        # Another credit card
        CreditCardFactory(owners=[another_user])

        card_1 = CreditCard.objects.get_card_for_owner(
            pk=credit_card.pk, username=owner_1.username
        )

        self.assertEqual(credit_card.id, card_1.id)
        self.assertIn(owner_1, credit_card.owners.all())

        card_2 = CreditCard.objects.get_card_for_owner(
            pk=credit_card.pk, username=owner_1.username
        )

        self.assertEqual(credit_card.id, card_2.id)
        self.assertIn(owner_2, credit_card.owners.all())

    def test_models_credit_card_demote_a_credit_card_from_main_is_forbidden(self):
        """Demote a main credit card is forbidden"""
        user = UserFactory()
        card = CreditCardFactory(owners=[user])

        ownership = card.ownerships.get(owner=user)

        self.assertTrue(ownership.is_main)

        with self.assertRaises(ValidationError) as context:
            ownership.is_main = False
            ownership.save()

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Demote a main credit card is forbidden']}",
        )

    def test_models_credit_card_delete_unused(self):
        """
        The manager method `delete_unused` should
        unlink cards that are linked to orders that won't need payment anymore,
        and delete all the credit cards that are not linked to any order.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            OrderFactory(state=state, product__price=10)

        # With this order factory, we create a credit card for all states
        self.assertEqual(CreditCard.objects.count(), len(enums.ORDER_STATE_CHOICES))

        unlinked_credit_cards, deleted_credit_cards = CreditCard.objects.delete_unused()

        # Order states that should not have a credit card linked
        no_card_order_states = enums.ORDER_INACTIVE_STATES + (
            enums.ORDER_STATE_COMPLETED,
        )
        self.assertEqual(len(unlinked_credit_cards), len(no_card_order_states))
        self.assertEqual(len(deleted_credit_cards), len(no_card_order_states))

        self.assertFalse(
            Order.objects.filter(
                state__in=no_card_order_states, credit_card__isnull=False
            ).exists()
        )
        self.assertFalse(
            CreditCard.objects.filter(orders__state__in=no_card_order_states).exists()
        )

    def test_models_credit_card_owner_field_is_removed(self):
        """
        The `owner` field of the CreditCard is removed, it should raise an error if
        when we want to set a User.
        """
        with self.assertRaises(FieldError) as context:
            CreditCardFactory(owner=UserFactory())

        self.assertEqual(
            str(context.exception),
            "Invalid field name(s) for model CreditCard: 'owner'.",
        )

    def test_models_credit_card_is_main_field_is_removed(self):
        """
        The `is_main` field of the CreditCard is removed, it should raise an error if
        when we want to set a boolean value.
        """
        with self.assertRaises(FieldError) as context:
            CreditCardFactory(is_main=True)

        self.assertEqual(
            str(context.exception),
            "Invalid field name(s) for model CreditCard: 'is_main'.",
        )
