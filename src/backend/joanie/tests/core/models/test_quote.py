"""Test suite for quote model."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from joanie.core.factories import QuoteFactory
from joanie.tests.base import LoggingTestCase


class QuoteModelsTestCase(LoggingTestCase):
    """Test suite for quote model."""

    def test_models_quote_property_is_signed_by_organization(self):
        """
        When the quote is signed by the organization, property `is_signed_by_organization`
        should return True
        """
        quote = QuoteFactory(organization_signed_on=timezone.now())

        self.assertTrue(quote.is_signed_by_organization)

    def test_models_quote_buyer_must_sign_before_purchase_order_accepted(self):
        """
        If organization has not signed the quote yet, we are not allowed to
        confirm that the purchase order has been received.
        """
        with self.assertRaises(ValidationError) as context:
            QuoteFactory(
                organization_signed_on=None,
                has_purchase_order=True,
            )

        self.assertTrue(
            "Organization must sign quote before receiving purchase order."
            in str(context.exception)
        )

    def test_models_quote_context_should_be_generated_before_organization_signed_on(
        self,
    ):
        """
        The organization should not be able to sign the quote before the context has been
        generated for the quote.
        """
        with self.assertRaises(ValidationError) as context:
            QuoteFactory(context=None, organization_signed_on=timezone.now())

        self.assertTrue(
            "You must generate the quote context before signing the quote."
            in str(context.exception)
        )
