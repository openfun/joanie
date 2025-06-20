"""Utils to generate the context quote document used for a batch order"""

from datetime import timedelta

from django.conf import settings
from django.utils.duration import duration_iso_string
from django.utils.translation import gettext as _

from babel.numbers import get_currency_symbol

from joanie.core.models import DocumentImage
from joanie.core.utils import file_checksum

# Prepare fallback content for debugging view purposes
QUOTE_FALLBACK_DATA = {
    "body": _("<QUOTE_BODY>"),
    "name": _("<QUOTE_NAME>"),
    "title": _("<QUOTE_TITLE>"),
    "description": _("<QUOTE_DESCRIPTION>"),
}

BATCH_ORDER_FALLBACK_DATA = {
    "nb_seats": _("<BATCH_ORDER_NB_SEATS>"),
}

COURSE_FALLBACK_DATA = {
    "name": _("<COURSE_NAME>"),
    "code": _("<COURSE_CODE>"),
    "effort": _("<COURSE_EFFORT>"),
    "price": _("<COURSE_PRICE>"),
    "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
}

CUSTOMER_FALLBACK_DATA = {
    "identification_number": _("<CUSTOMER_IDENTIFICATION_NUMBER>"),
    "company_name": _("<CUSTOMER_COMPANY_NAME>"),
    "address": _("<CUSTOMER_ADDRESS>"),
    "postcode": _("<CUSTOMER_POSTCODE>"),
    "country": _("<CUSTOMER_COUNTRY>"),
    "city": _("<CUSTOMER_CITY>"),
}

ORGANIZATION_FALLBACK_DATA = {
    "logo": (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
        "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
    ),
    "address": {
        "address": _("<ORGANIZATION_ADDRESS_STREET_NAME>"),
        "city": _("<ORGANIZATION_ADDRESS_CITY>"),
        "country": _("<ORGANIZATION_ADDRESS_COUNTRY>"),
        "last_name": _("<ORGANIZATION_LAST_NAME>"),
        "first_name": _("<ORGANIZATION_FIRST_NAME>"),
        "postcode": _("<ORGANIZATION_ADDRESS_POSTCODE>"),
        "title": _("<ORGANIZATION_ADDRESS_TITLE>"),
        "is_main": True,
    },
    "name": _("<ORGANIZATION_NAME>"),
    "enterprise_code": _("<ORGANIZATION_ENTERPRISE_CODE>"),
    "activity_code": _("<ORGANIZATION_ACTIVITY_CODE>"),
    "signatory_representative": _("<SIGNATORY_REPRESENTATIVE>"),
    "signatory_representative_profession": _("<SIGNATURE_REPRESENTATIVE_PROFESSION>"),
    "contact_phone": _("<CONTACT_PHONE>"),
    "contact_email": _("<CONTACT_EMAIL>"),
}


def prepare_organization_logo(quote):
    """Prepare the organization logo"""
    logo_checksum = file_checksum(quote.batch_order.organization.logo)
    logo_image, created = DocumentImage.objects.get_or_create(
        checksum=logo_checksum,
        defaults={"file": quote.batch_order.organization.logo},
    )

    if created:
        quote.definition.images.set([logo_image])

    organization_logo_id = str(logo_image.id)

    return organization_logo_id


def prepare_organization_address(organization):
    """Return the serialized organization address"""
    # pylint: disable=cyclic-import, import-outside-toplevel
    from joanie.core.models import Address
    from joanie.core.serializers.client import AddressSerializer

    try:
        organization_address = organization.addresses.get(is_main=True)
    except Address.DoesNotExist:
        organization_address = None
    if organization_address:
        organization_address = AddressSerializer(organization_address).data

    return organization_address


def prepare_organization_context(language_code, organization, logo: str):
    """Prepare organization data"""
    organization_address = prepare_organization_address(organization)

    organization_data = {
        "address": organization_address,
        "logo_id": logo,
        "name": organization.safe_translation_getter(
            "title", language_code=language_code
        ),
        "enterprise_code": organization.enterprise_code,
        "activity_category_code": (organization.activity_category_code),
        "signatory_representative": organization.signatory_representative,
        "signatory_representative_profession": (
            organization.signatory_representative_profession
        ),
        "contact_phone": organization.contact_phone,
        "contact_email": organization.contact_email,
    }

    return organization_data


def prepare_batch_order_context(quote):
    """Prepare the context of the batch order"""
    batch_order_context = {
        "nb_seats": quote.batch_order.nb_seats,
    }

    return batch_order_context


def prepare_course_context(language_code, batch_order):
    """Prepare course context for the document generation"""
    course_effort = batch_order.offer.course.effort
    # Transform duration value to ISO 8601 format
    if isinstance(course_effort, timedelta):
        course_effort = duration_iso_string(course_effort)

    return {
        "name": batch_order.offer.product.safe_translation_getter(
            "title", language_code=language_code
        ),
        "code": batch_order.offer.course.code,
        "effort": course_effort,
        "price": str(batch_order.total),
        "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
    }


def prepare_customer_context(batch_order):
    """Prepare the customer's context"""
    return {
        "identification_number": batch_order.identification_number,
        "company": batch_order.company_name,
        "address": batch_order.address,
        "postcode": batch_order.postcode,
        "country": str(batch_order.country.code),
        "city": batch_order.city,
    }


def generate_document_context(quote=None):
    """Generate quote document context"""
    language_code = (
        quote.batch_order.quote.definition.language if quote else settings.LANGUAGE_CODE
    )

    document_context = {
        "quote": QUOTE_FALLBACK_DATA,
        "batch_order": BATCH_ORDER_FALLBACK_DATA,
        "course": COURSE_FALLBACK_DATA,
        "customer": CUSTOMER_FALLBACK_DATA,
        "organization": ORGANIZATION_FALLBACK_DATA,
    }

    if quote:
        logo = prepare_organization_logo(quote)
        document_context.update(
            {
                "quote": {
                    "name": quote.definition.name,
                    "title": quote.definition.title,
                    "description": quote.definition.description,
                    "body": quote.definition.get_body_in_html(),
                },
                "batch_order": {
                    "nb_seats": quote.batch_order.nb_seats,
                },
                "course": prepare_course_context(
                    language_code=language_code, batch_order=quote.batch_order
                ),
                "customer": prepare_customer_context(batch_order=quote.batch_order),
                "organization": prepare_organization_context(
                    language_code=language_code,
                    organization=quote.batch_order.organization,
                    logo=logo,
                ),
            },
        )

    return document_context
