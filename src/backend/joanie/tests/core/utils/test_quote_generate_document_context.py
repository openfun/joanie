"""Test suite for Quote generate document context"""

from datetime import timedelta

from django.conf import settings
from django.test import TestCase

from babel.numbers import get_currency_symbol

from joanie.core import factories, models
from joanie.core.utils.quotes import generate_document_context


class UtilsQuoteGenerateContextDocument(TestCase):
    """Test suite for Quote generate document context"""

    maxDiff = None

    def test_utils_quote_generate_document_with_placeholders(
        self,
    ):
        """
        Batch order quote utils 'generate context document' method should return the quote's
        context with the quote context with placeholders when no quote is passed.
        """
        expected_context = {
            "quote": {
                "body": "&lt;QUOTE_BODY&gt;",
                "title": "<QUOTE_TITLE>",
                "description": "<QUOTE_DESCRIPTION>",
            },
            "batch_order": {
                "nb_seats": "<BATCH_ORDER_NB_SEATS>",
            },
            "course": {
                "name": "<COURSE_NAME>",
                "code": "<COURSE_CODE>",
                "effort": "<COURSE_EFFORT>",
                "price": "<COURSE_PRICE>",
                "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
            },
            "customer": {
                "representative_name": "<CUSTOMER_REPRESENTATIVE_NAME>",
                "identification_number": "<CUSTOMER_IDENTIFICATION_NUMBER>",
                "company_name": "<CUSTOMER_COMPANY_NAME>",
                "address": "<CUSTOMER_ADDRESS>",
                "postcode": "<CUSTOMER_POSTCODE>",
                "country": "<CUSTOMER_COUNTRY>",
                "city": "<CUSTOMER_CITY>",
            },
            "organization": {
                "address": {
                    "address": "<ORGANIZATION_ADDRESS_STREET_NAME>",
                    "city": "<ORGANIZATION_ADDRESS_CITY>",
                    "country": "<ORGANIZATION_ADDRESS_COUNTRY>",
                    "last_name": "<ORGANIZATION_LAST_NAME>",
                    "first_name": "<ORGANIZATION_FIRST_NAME>",
                    "postcode": "<ORGANIZATION_ADDRESS_POSTCODE>",
                    "title": "<ORGANIZATION_ADDRESS_TITLE>",
                    "is_main": True,
                },
                "name": "<ORGANIZATION_NAME>",
                "enterprise_code": "<ORGANIZATION_ENTERPRISE_CODE>",
                "activity_category_code": "<ORGANIZATION_ACTIVITY_CODE>",
                "representative": "<REPRESENTATIVE>",
                "signatory_representative": "<SIGNATORY_REPRESENTATIVE>",
                "signatory_representative_profession": "<SIGNATURE_REPRESENTATIVE_PROFESSION>",
                "contact_phone": "<CONTACT_PHONE>",
                "contact_email": "<CONTACT_EMAIL>",
                "logo": (
                    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
                    "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
                ),
            },
        }

        context = generate_document_context(quote=None)

        self.assertEqual(context, expected_context)

    def test_utils_quote_generate_document(self):
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
        batch_order = factories.BatchOrderFactory(
            organization=organization,
            offering__course=factories.CourseFactory(
                effort=timedelta(hours=10, minutes=30, seconds=12),
            ),
            offering__product__price="151.00",
            nb_seats=2,
        )
        batch_order.init_flow()
        quote = factories.QuoteFactory(batch_order=batch_order)

        expected_context = {
            "quote": {
                "title": quote.definition.title,
                "description": quote.definition.description,
                "body": quote.definition.get_body_in_html(),
            },
            "batch_order": {
                "nb_seats": batch_order.nb_seats,
            },
            "course": {
                "name": batch_order.relation.product.title,
                "code": batch_order.relation.course.code,
                "effort": "P0DT10H30M12S",
                "price": "302.00",
                "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
            },
            "customer": {
                "representative_name": batch_order.owner.name,
                "identification_number": batch_order.identification_number,
                "company_name": batch_order.company_name,
                "address": batch_order.address,
                "postcode": batch_order.postcode,
                "country": str(batch_order.country.code),
                "city": batch_order.city,
            },
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
                "representative": organization.representative,
                "activity_category_code": organization.activity_category_code,
                "signatory_representative": organization.signatory_representative,
                "signatory_representative_profession": (
                    organization.signatory_representative_profession
                ),
                "contact_phone": organization.contact_phone,
                "contact_email": organization.contact_email,
            },
        }

        context = generate_document_context(quote=quote)

        organization_logo = models.DocumentImage.objects.get()
        expected_context["organization"]["logo_id"] = str(organization_logo.id)

        self.assertEqual(context, expected_context)
