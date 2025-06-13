"""Test suite for Quote generate document context"""

from decimal import Decimal as D

from django.conf import settings
from django.test import TestCase

from babel.numbers import get_currency_symbol

from joanie.core import factories
from joanie.core.models import DocumentImage
from joanie.core.utils import quote as quote_utils


class UtilsQuoteGenerateContextDocument(TestCase):
    """Test suite for Quote generate document context"""

    maxDiff = None

    def test_utils_batch_order_quote_generate_document_with_placeholders(
        self,
    ):
        """
        Batch order quote utils 'generate context document' method should return the quote's
        context with the quote context with placeholders when no quote is passed.
        """
        expected_context = {
            "quote": {
                "body": "<QUOTE_BODY>",
                "name": "<QUOTE_NAME>",
                "title": "<QUOTE_TITLE>",
                "description": "<QUOTE_DESCRIPTION>",
            },
            "batch_order": {
                "nb_seats": "<BATCH_ORDER_NB_SEATS>",
                "discount": "<BATCH_ORDER_DISCOUNT>",
                "vat_amount": "<BATCH_ORDER_VAT_AMOUNT>",
                "net_amount": "<BATCH_ORDER_NET_AMOUNT>",
                "total": "<BATCH_ORDER_TOTAL>",
                "currency": "<BATCH_ORDER_CURRENCY>",
            },
            "product": {
                "name": "<PRODUCT_NAME>",
                "description": "<PRODUCT_DESCRIPTION>",
            },
            "customer": {
                "identification_number": "<CUSTOMER_IDENTIFICATION_NUMBER>",
                "company_name": "<CUSTOMER_COMPANY_NAME>",
                "address": "<CUSTOMER_ADDRESS>",
                "postcode": "<CUSTOMER_POSTCODE>",
                "country": "<CUSTOMER_COUNTRY>",
                "city": "<CUSTOMER_CITY>",
            },
            "seller": settings.JOANIE_INVOICE_SELLER_ADDRESS,
            "organization": {
                "address": "<ORGANIZATION_ADDRESS>",
                "name": "<ORGANIZATION_NAME>",
                "enterprise_code": "<ORGANIZATION_ENTERPRISE_CODE>",
                "activity_code": "<ORGANIZATION_ACTIVITY_CODE>",
                "logo": (
                    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
                    "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
                ),
            },
        }

        context = quote_utils.generate_document_context(quote=None)

        self.assertEqual(context, expected_context)

    def test_utils_batch_order_quote_generate_document(self):
        """
        Batch order quote utils 'generate context document' method should return the quote's
        context for the document.
        """
        organization = factories.OrganizationFactory(
            enterprise_code="1234",
            activity_category_code="abcd1234",
        )
        address_organization = factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            is_main=True,
            is_reusable=True,
        )
        batch_order = factories.BatchOrderFactory(organization=organization)
        batch_order.init_flow()
        quote = factories.QuoteFactory(batch_order=batch_order)

        vat = D(settings.JOANIE_VAT)
        vat_amount = quote.batch_order.total * vat / 100
        net_amount = quote.batch_order.total - vat_amount

        expected_context = {
            "quote": {
                "name": quote.definition.name,
                "title": quote.definition.title,
                "description": quote.definition.description,
                "body": quote.definition.get_body_in_html(),
            },
            "batch_order": {
                "nb_seats": batch_order.nb_seats,
                "discount": None,
                "vat_amount": vat_amount,
                "net_amount": net_amount,
                "total": batch_order.total,
                "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
            },
            "product": {
                "name": batch_order.relation.product.title,
                "description": batch_order.relation.product.description,
            },
            "customer": {
                "identification_number": batch_order.identification_number,
                "company": batch_order.company_name,
                "address": batch_order.address,
                "postcode": batch_order.postcode,
                "country": str(batch_order.country.code),
                "city": batch_order.city,
            },
            "seller": settings.JOANIE_INVOICE_SELLER_ADDRESS,
            "organization": {
                "address": {
                    "id": str(address_organization.id),
                    "address": address_organization.address,
                    "city": address_organization.city,
                    "country": str(address_organization.country.code),
                    "last_name": address_organization.last_name,
                    "first_name": address_organization.first_name,
                    "postcode": address_organization.postcode,
                    "title": address_organization.title,
                    "is_main": address_organization.is_main,
                },
                "name": organization.title,
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": organization.activity_category_code,
            },
        }

        context = quote_utils.generate_document_context(quote=quote)

        organization_logo = DocumentImage.objects.get()
        expected_context["organization"]["logo_id"] = str(organization_logo.id)

        self.assertEqual(context, expected_context)
