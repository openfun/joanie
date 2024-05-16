"""Test suite for the `CreditCard` Manager."""

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
        If the `pk` and the `owner_id` matches an existing credit card, the manager
        method `get_card_for_owner` of the `CreditCard` model should return the object.
        When it does not match any objects in the database, it should raise the error
        CreditCard.DoesNotExist.
        """
        user = UserFactory()
        credit_card = CreditCardFactory(owner=user)
        another_user = UserFactory()
        credit_card_other_owner = CreditCardFactory(owner=another_user)

        credit_card = CreditCard.objects.get_card_for_owner(
            pk=credit_card.pk, owner_id=user.id
        )

        self.assertEqual(credit_card.owner, user)

        with self.assertRaises(CreditCard.DoesNotExist) as context:
            CreditCard.objects.get_card_for_owner(
                pk=credit_card_other_owner.id, owner_id=user.id
            )

        self.assertEqual(
            str(context.exception), "CreditCard matching query does not exist."
        )
