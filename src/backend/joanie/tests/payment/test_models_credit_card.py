"""Test suite for the `CreditCard` Manager."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core.factories import UserFactory
from joanie.payment.factories import CreditCardFactory
from joanie.payment.models import CreditCard


class CreditCardModelTestCase(TestCase):
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
        payment_provider = "dummy"
        credit_card = CreditCardFactory(owner=user, payment_provider=payment_provider)
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
