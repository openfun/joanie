"""Utils to generate the context quote document used for a batch order"""

from datetime import timedelta

from django.conf import settings
from django.utils.duration import duration_iso_string
from django.utils.translation import gettext as _

from joanie.core.models import DocumentImage
from joanie.core.utils import file_checksum

QUOTE_FALLBACK_DATA = {
    "title": _("<QUOTE_TITLE>"),
    "description": _("<QUOTE_DESCRIPTION>"),
    "body": _("&lt;QUOTE_BODY&gt;"),
}

BATCH_ORDER_FALLBACK_DATA = {
    "nb_seats": _("<BATCH_ORDER_NB_SEATS>"),
}

COURSE_FALLBACK_DATA = {
    "name": _("<COURSE_NAME>"),
    "code": _("<COURSE_CODE>"),
    "effort": _("<COURSE_EFFORT>"),
}

CUSTOMER_FALLBACK_DATA = {
    "representative_name": _("<CUSTOMER_REPRESENTATIVE_NAME>"),
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
    "activity_category_code": _("<ORGANIZATION_ACTIVITY_CODE>"),
    "representative": _("<REPRESENTATIVE>"),
    "signatory_representative": _("<SIGNATORY_REPRESENTATIVE>"),
    "signatory_representative_profession": _("<SIGNATURE_REPRESENTATIVE_PROFESSION>"),
    "contact_phone": _("<CONTACT_PHONE>"),
    "contact_email": _("<CONTACT_EMAIL>"),
}


def prepare_organization_logo(definition: "QuoteDefinition", organization):
    """Prepare the organization logo"""

    logo_checksum = file_checksum(organization.logo)
    logo_image, created = DocumentImage.objects.get_or_create(
        checksum=logo_checksum,
        defaults={"file": organization.logo},
    )
    if created:
        definition.images.set([logo_image])
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
        "activity_category_code": organization.activity_category_code,
        "representative": organization.representative,
        "signatory_representative": organization.signatory_representative,
        "signatory_representative_profession": (
            organization.signatory_representative_profession
        ),
        "contact_phone": organization.contact_phone,
        "contact_email": organization.contact_email,
    }

    return organization_data


def prepare_course_context(language_code, batch_order):
    """Prepare course context for the document generation"""
    course_effort = batch_order.offering.course.effort
    # Transform duration value to ISO 8601 format
    if isinstance(course_effort, timedelta):
        course_effort = duration_iso_string(course_effort)

    return {
        "name": batch_order.offering.product.safe_translation_getter(
            "title", language_code=language_code
        ),
        "code": batch_order.offering.course.code,
        "effort": course_effort,
    }


def prepare_customer_context(batch_order):
    """Prepare the customer's context"""
    return {
        "representative_name": batch_order.owner.name,
        "identification_number": batch_order.identification_number,
        "company_name": batch_order.company_name,
        "address": batch_order.address,
        "postcode": batch_order.postcode,
        "country": str(batch_order.country.code),
        "city": batch_order.city,
    }


def generate_document_context(quote_definition=None, batch_order=None):
    """Generate quote document context"""
    language_code = (
        quote_definition.language if quote_definition else settings.LANGUAGE_CODE
    )

    document_context = {
        "quote": QUOTE_FALLBACK_DATA,
        "batch_order": BATCH_ORDER_FALLBACK_DATA,
        "course": COURSE_FALLBACK_DATA,
        "customer": CUSTOMER_FALLBACK_DATA,
        "organization": ORGANIZATION_FALLBACK_DATA,
    }

    if quote_definition:
        logo = prepare_organization_logo(
            definition=quote_definition, organization=batch_order.organization
        )
        document_context.update(
            {
                "quote": {
                    "title": quote_definition.title,
                    "description": quote_definition.description,
                    "body": quote_definition.get_body_in_html(),
                },
                "batch_order": {
                    "nb_seats": batch_order.nb_seats,
                },
                "course": prepare_course_context(
                    language_code=language_code, batch_order=batch_order
                ),
                "customer": prepare_customer_context(batch_order=batch_order),
                "organization": prepare_organization_context(
                    language_code=language_code,
                    organization=batch_order.organization,
                    logo=logo,
                ),
            },
        )

    return document_context
