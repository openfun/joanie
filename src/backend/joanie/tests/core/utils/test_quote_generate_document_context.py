"""Test suite for Quote generate document context"""

import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.test import TestCase

from PIL import Image

from joanie.core import enums, factories, models
from joanie.core.utils.quotes import generate_document_context
from joanie.tests.compare_image_utils import (
    call_issuers_generate_document,
    clear_generated_files,
    compare_images,
    convert_pdf_to_png,
)

LOGO_FALLBACK = (
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
    "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
)


def generate_batch_order():
    """Create a batch order and related quote with consistent data"""
    user = factories.UserFactory(
        email="student@example.fr",
        first_name="Rooky",
        last_name="The Student",
        phone_number="0612345678",
    )
    organization = factories.OrganizationFactory(
        title="University X",
        dpo_email="dpojohnnydoes@example.fr",
        contact_email="contact@example.fr",
        contact_phone="0123456789",
        enterprise_code="ENTRCODE1234",
        activity_category_code="ACTCATCODE1234",
        representative="John Doe",
        representative_profession="Educational representative",
        signatory_representative="Big boss",
        signatory_representative_profession="Director",
    )
    address_organization = factories.OrganizationAddressFactory(
        organization=organization,
        owner=None,
        address="1 Rue de l'Université",
        postcode="75000",
        city="Paris",
        country="FR",
        is_reusable=True,
        is_main=True,
    )
    language_code = "en-us"
    batch_order = factories.BatchOrderFactory(
        owner=user,
        organization=organization,
        offering__course=factories.CourseFactory(
            effort=timedelta(hours=10, minutes=30, seconds=12),
            code="00002",
        ),
        nb_seats=2,
        offering__product__title="You know nothing Jon Snow",
        offering__product__quote_definition=factories.QuoteDefinitionFactory(
            name=enums.QUOTE_DEFAULT,
            title="Quote Test",
            description="A quote for the batch order",
            body="Article of the quote",
            language=language_code,
        ),
        state=enums.BATCH_ORDER_STATE_QUOTED,
        vat_registration="VAT_NUMBER_123",
        company_name="Acme Org",
        address="Street of awesomeness",
        postcode="00000",
        city="Unknown City",
        country="FR",
        identification_number="ABC_ID_NUM_TEST",
        administrative_firstname="Jon",
        administrative_lastname="Snow",
        administrative_profession="Buyer",
        administrative_email="jonsnow@example.acme",
        administrative_telephone="0123457890",
        signatory_firstname="Janette",
        signatory_lastname="Doe",
        signatory_email="janette@example.acme",
        signatory_telephone="0987654321",
        signatory_profession="Manager",
        payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
    )

    batch_order.freeze_total(Decimal("302.00"))

    return batch_order, organization, address_organization


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
                "reference": "<REFERENCE>",
            },
            "batch_order": {
                "nb_seats": "<BATCH_ORDER_NB_SEATS>",
            },
            "course": {
                "name": "<COURSE_NAME>",
                "code": "<COURSE_CODE>",
                "effort": "<COURSE_EFFORT>",
            },
            "customer": {
                "representative_name": "<CUSTOMER_REPRESENTATIVE_NAME>",
                "identification_number": "<CUSTOMER_IDENTIFICATION_NUMBER>",
                "vat_registration": "<CUSTOMER_VAT_REGISTRATION>",
                "company_name": "<CUSTOMER_COMPANY_NAME>",
                "address": "<CUSTOMER_ADDRESS>",
                "postcode": "<CUSTOMER_POSTCODE>",
                "country": "<CUSTOMER_COUNTRY>",
                "city": "<CUSTOMER_CITY>",
                "billing_address": {
                    "address": "<BILLING_ADDRESS>",
                    "postcode": "<BILLING_POSTCODE>",
                    "city": "<BILLING_CITY>",
                    "country": "<BILLING_COUNTRY>",
                    "company_name": "<BILLING_COMPANY_NAME>",
                    "contact_name": "<BILLING_CONTACT_NAME>",
                    "contact_email": "<BILLING_CONTACT_EMAIL>",
                },
                "administrative_firstname": "<ADMIN_FIRSTNAME>",
                "administrative_lastname": "<ADMIN_LASTNAME>",
                "administrative_profession": "<ADMIN_PROFESSION>",
                "administrative_email": "<ADMIN_EMAIL>",
                "administrative_telephone": "<ADMIN_TELEPHONE>",
                "funding_entity": "<FUNDING_ENTITY>",
                "funding_amount": "<FUNDING_AMOUNT>",
                "currency": "<DEFAULT_CURRENCY>",
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

        context = generate_document_context()

        self.assertEqual(expected_context, context)

    def test_utils_quote_generate_document_context(self):
        """
        Batch order quote utils 'generate context document' method should return the quote's
        context for the document.
        """
        batch_order, organization, address_organization = generate_batch_order()

        expected_context = {
            "quote": {
                "title": batch_order.quote.definition.title,
                "description": batch_order.quote.definition.description,
                "body": batch_order.quote.definition.get_body_in_html(),
                "reference": batch_order.quote.reference,
            },
            "batch_order": {
                "nb_seats": batch_order.nb_seats,
            },
            "course": {
                "name": batch_order.relation.product.title,
                "code": batch_order.relation.course.code,
                "effort": "P0DT10H30M12S",
            },
            "customer": {
                "representative_name": batch_order.owner.name,
                "identification_number": batch_order.identification_number,
                "vat_registration": batch_order.vat_registration,
                "company_name": batch_order.company_name,
                "address": batch_order.address,
                "postcode": batch_order.postcode,
                "country": str(batch_order.country.code),
                "city": batch_order.city,
                "billing_address": {
                    "company_name": batch_order.billing_address["company_name"],
                    "address": batch_order.billing_address["address"],
                    "postcode": batch_order.billing_address["postcode"],
                    "city": batch_order.billing_address["city"],
                    "country": batch_order.billing_address["country"],
                    "contact_name": batch_order.billing_address["contact_name"],
                    "contact_email": batch_order.billing_address["contact_email"],
                },
                "administrative_firstname": batch_order.administrative_firstname,
                "administrative_lastname": batch_order.administrative_lastname,
                "administrative_profession": batch_order.administrative_profession,
                "administrative_email": batch_order.administrative_email,
                "administrative_telephone": batch_order.administrative_telephone,
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
                "currency": "€",
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

        context = generate_document_context(
            quote_definition=batch_order.quote.definition, batch_order=batch_order
        )

        organization_logo = models.DocumentImage.objects.get()
        expected_context["organization"]["logo_id"] = str(organization_logo.id)

        self.assertEqual(expected_context, context)

    def test_utils_issuers_verify_document_quote_default_style(self):
        """
        When generating the template quote default, the style of the document should
        match the original one.
        """
        base_path = settings.BASE_DIR + "/joanie/tests/core/utils/__diff__/"

        batch_order, _, _ = generate_batch_order()

        context = generate_document_context(
            quote_definition=batch_order.quote.definition,
            batch_order=batch_order,
        )
        context["organization"]["logo"] = LOGO_FALLBACK

        pdf_path = call_issuers_generate_document(
            name=batch_order.quote.definition.name,
            context=context,
            path=base_path,
        )

        generated_image_path = convert_pdf_to_png(pdf_path)
        generated_image = Image.open(generated_image_path).convert("RGB")

        os.remove(base_path + batch_order.quote.definition.name + ".pdf")

        original_image = Image.open(
            base_path + batch_order.quote.definition.name + "_original.png"
        ).convert("RGB")

        self.assertEqual(generated_image.size, original_image.size)

        diff = compare_images(
            generated_image,
            original_image,
            base_path + batch_order.quote.definition.name + "_diff.png",
        )
        self.assertLessEqual(
            diff,
            1.5,
            f"""
            Test failed since the images are different, if you want to keep the new version use
            mv -f {base_path}quote_default.png
            {base_path}quote_defaultoriginal.png
            rm -f {base_path}quote_default_diff.png
            """,
        )

        clear_generated_files(base_path, batch_order.quote.definition.name)
