"""Test suite for quote model."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from joanie.core.factories import QuoteFactory
from joanie.tests.base import LoggingTestCase


class QuoteModelsTestCase(LoggingTestCase):
    """Test suite for quote model."""

    def test_models_quote_organization_should_sign_before_buyer(self):
        """
        The buyer cannot sign the quote before the organization has signed.
        """
        with self.assertRaises(ValidationError) as context:
            QuoteFactory(buyer_signed_on=timezone.now(), organization_signed_on=None)

        self.assertTrue(
            "Organization must sign quote before the buyer." in str(context.exception)
        )

    def test_models_quote_buyer_must_sign_before_purchase_order_accepted(self):
        """
        If organization and buyer haven't signed the quote yet, we are not allowed to
        confirm that the purchase order has been received.
        """
        with self.assertRaises(ValidationError) as context:
            QuoteFactory(
                organization_signed_on=None,
                buyer_signed_on=None,
                has_purchase_order_received=True,
            )

        self.assertTrue(
            "Both parties must sign quote before confirming the purchase order."
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
