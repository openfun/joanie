"""Test suite for batch order quote model."""

from django.conf import settings
from django.test import override_settings

from babel.numbers import get_currency_symbol
from stockholm import Money

from joanie.core.factories import BatchOrderFactory, BatchOrderQuoteFactory
from joanie.tests.base import LoggingTestCase


class BatchOrderModelsTestCase(LoggingTestCase):
    """Test suite for batch order quote model."""

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_models_batch_order_quote_localized_context(self):
        """
        When a batch order quote is created, localized contexts in each enabled languages should
        be created and set into the field `localized_context`.
        """
        batch_order = BatchOrderFactory(relation__product__title="Product 1")
        batch_order.relation.product.translations.create(
            language_code="fr-fr", title="Produit 1"
        )
        batch_order.relation.product.translations.create(
            language_code="de-de", title="Produkt 1"
        )

        quote = BatchOrderQuoteFactory(batch_order=batch_order)

        self.assertDictEqual(
            quote.localized_context,
            {
                "en-us": {
                    "product": {
                        "description": batch_order.relation.product.description,
                        "name": batch_order.relation.product.title,
                    },
                },
                "fr-fr": {
                    "product": {
                        "description": "",
                        "name": "Produit 1",
                    },
                },
                "de-de": {
                    "product": {
                        "description": "",
                        "name": "Produkt 1",
                    },
                },
            },
        )

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
        ),
        LANGUAGE_CODE="fr-fr",
        DEFAULT_CURRENCY="EUR",
        JOANIE_VAT=20,
    )
    def test_models_batch_order_quote_get_document_context(self):
        """
        Get document context should generate the context data to use for the quote document.
        It should use the language code setted for the localized context entry.
        """
        batch_order = BatchOrderFactory(
            relation__product__title="Produit 1",
            relation__product__price=10,
            nb_seats=10,
        )
        batch_order.relation.product.translations.create(
            language_code="en-us", title="Product 1"
        )

        quote = BatchOrderQuoteFactory(batch_order=batch_order)

        vat_amount = batch_order.total * settings.JOANIE_VAT / 100
        net_amount = batch_order.total - vat_amount
        currency = get_currency_symbol(settings.DEFAULT_CURRENCY)

        context = quote.get_document_context()

        self.assertEqual(
            context,
            {
                "metadata": {
                    "issued_on": quote.updated_on,
                    "reference": quote.reference,
                },
                "amount": {
                    "nb_seats": quote.batch_order.nb_seats,
                    "discount": None,
                    "vat_amount": vat_amount,
                    "net_amount": net_amount,
                    "total": Money(quote.batch_order.total),
                    "currency": currency,
                },
                "customer": {
                    "identification_number": quote.batch_order.identification_number,
                    "company": quote.batch_order.company_name,
                    "address": quote.batch_order.address,
                    "postcode": quote.batch_order.postcode,
                    "country": quote.batch_order.country,
                    "city": quote.batch_order.city,
                },
                "seller": {
                    "address": settings.JOANIE_INVOICE_SELLER_ADDRESS,
                },
                "product": {
                    "description": "",
                    "name": "Produit 1",
                },
            },
        )
