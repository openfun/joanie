"""Test suite for quote model."""

import threading
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

import pytest

from joanie.core import enums
from joanie.core.factories import (
    BatchOrderFactory,
    QuoteDefinitionFactory,
    QuoteFactory,
)
from joanie.core.models import Quote, QuoteDefinition
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

    def test_models_quote_purchase_order_reference_must_be_provided_once_quote_is_signed(
        self,
    ):
        """
        The organization must provide the purchase order reference once the quote is signed
        and has purchase order is set to True, otherwise it should return a `ValidationError`.
        """
        with self.assertRaises(ValidationError) as context:
            QuoteFactory(
                has_purchase_order=True,
                organization_signed_on=timezone.now(),
                purchase_order_reference=None,
            )

        self.assertTrue(
            "If a purchase order is received, the organization must have signed "
            "and a purchase order reference must be set." in str(context.exception)
        )

    def test_models_purchase_order_reference_in_relation_with_batch_order_payment_methods(
        self,
    ):
        """
        The purchase order reference should only be set when the related batch order
        uses `purchase_order` payment method. Otherwise, it should not be set.
        """
        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            quote = BatchOrderFactory(
                payment_method=payment_method, state=enums.BATCH_ORDER_STATE_TO_SIGN
            ).quote
            if payment_method in [
                enums.BATCH_ORDER_WITH_BANK_TRANSFER,
                enums.BATCH_ORDER_WITH_CARD_PAYMENT,
            ]:
                self.assertIsNone(quote.purchase_order_reference)
            else:
                self.assertIsNotNone(quote.purchase_order_reference)

    @override_settings(JOANIE_PREFIX_QUOTE_REFERENCE="JOANIE")
    def test_models_quote_reference_uniqueness(self):
        """Everytime a quote object is created, the reference should be incremented by one"""

        with mock.patch(
            "django.utils.timezone.now",
            return_value=datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC")),
        ):
            quote_1 = QuoteFactory()

        self.assertEqual(quote_1.reference, "JOANIE_2025_0000000")

        with self.assertRaises(ValidationError) as context:
            QuoteFactory(reference="JOANIE_2025_0000000")

        self.assertTrue(
            "Quote with this Reference already exists." in str(context.exception)
        )

    def test_models_quote_purchase_order_reference_duplicates(self):
        """
        It should be possible to have two purchase order reference that are the same.
        This value is given by the buyer, it may happen that two references are the
        same in some rare cases.
        """
        quote_1 = QuoteFactory(
            purchase_order_reference="ABC_test_quote",
        )
        quote_2 = QuoteFactory(
            purchase_order_reference="ABC_test_quote",
        )

        self.assertEqual(Quote.objects.count(), 2)
        self.assertEqual(
            quote_1.purchase_order_reference, quote_2.purchase_order_reference
        )

    @override_settings(JOANIE_PREFIX_QUOTE_REFERENCE="JOANIE")
    def test_models_quote_reference_should_increment_by_1(self):
        """Everytime a quote object is created, the reference should be incremented by one"""

        with mock.patch(
            "django.utils.timezone.now",
            return_value=datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC")),
        ):
            quote_1 = QuoteFactory()
            quote_2 = QuoteFactory()
            quote_3 = QuoteFactory()

        self.assertEqual(quote_1.reference, "JOANIE_2025_0000000")
        self.assertEqual(quote_2.reference, "JOANIE_2025_0000001")
        self.assertEqual(quote_3.reference, "JOANIE_2025_0000002")


# pylint:disable=unused-argument
@override_settings(JOANIE_PREFIX_QUOTE_REFERENCE="JOANIE")
@pytest.mark.django_db(transaction=True)
def test_models_quote_generate_unique_reference_multiple_thread(transactional_db):
    """
    We want to ensure that when 2 requests are sent to create a Quote, the first
    creation locks the rows in the database for uniqueness of reference. Both object are
    created in the order of their arrival.
    """
    created_references = []
    mocked_now = datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
    Quote.objects.all().delete()

    # Create the seed of the first quote with reference number ends with "0000000"
    Quote.objects.create(
        definition=QuoteDefinitionFactory(),
        reference="JOANIE_2025_000000",
    )

    def create_quote():
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            quote = Quote(definition=QuoteDefinitionFactory())
            with transaction.atomic():
                quote.clean()
                quote.save()
                created_references.append(quote.reference)

    thread_1 = threading.Thread(target=create_quote)
    thread_2 = threading.Thread(target=create_quote)

    thread_1.start()
    thread_2.start()

    thread_1.join()
    thread_2.join()

    assert len(created_references) == 2  # noqa: PLR2004
    assert created_references[0] != created_references[1]
    assert created_references[0] == ("JOANIE_2025_0000001")
    assert created_references[1] == ("JOANIE_2025_0000002")

    Quote.objects.all().delete()
    QuoteDefinition.objects.all().delete()
