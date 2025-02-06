"""Test suite for the `CreditCard` Manager."""

from unittest import mock

from django.core.exceptions import ValidationError

from joanie.core.factories import UserFactory
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
        credit_card = CreditCardFactory(owner=user)
        another_user = UserFactory()
        another_credit_card = CreditCardFactory(owner=another_user)

        credit_card = CreditCard.objects.get_card_for_owner(
            pk=credit_card.pk, username=user.username
        )

        self.assertEqual(credit_card.owner, user)

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
        CreditCardFactory.create_batch(3, owner=owner)
        CreditCardFactory(owner=owner, payment_provider="lyra")
        another_owner = UserFactory()
        CreditCardFactory(owner=another_owner)

        results = CreditCard.objects.get_cards_for_owner(username=owner.username)

        # There should be 4 existing cards for the owner overall
        self.assertEqual(CreditCard.objects.filter(owner=owner).count(), 4)
        # But only 3 cards should be retrieve because of the active payment backend
        self.assertEqual(results.count(), 3)
        for card in results:
            self.assertEqual(card.payment_provider, "dummy")
            self.assertEqual(card.owner.id, owner.id)

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
