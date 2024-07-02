"""Utility to `generate document context` data"""

from copy import deepcopy
from datetime import date, timedelta

from django.conf import settings
from django.utils.duration import duration_iso_string
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from babel.numbers import get_currency_symbol

from joanie.core.models import DocumentImage
from joanie.core.utils import file_checksum, image_to_base64

# Organization section for generating contract definition
ORGANIZATION_FALLBACK_ADDRESS = {
    "address": _("<ORGANIZATION_ADDRESS_STREET_NAME>"),
    "city": _("<ORGANIZATION_ADDRESS_CITY>"),
    "country": _("<ORGANIZATION_ADDRESS_COUNTRY>"),
    "last_name": _("<ORGANIZATION_LAST_NAME>"),
    "first_name": _("<ORGANIZATION_FIRST_NAME>"),
    "postcode": _("<ORGANIZATION_ADDRESS_POSTCODE>"),
    "title": _("<ORGANIZATION_ADDRESS_TITLE>"),
    "is_main": True,
}

ORGANIZATION_FALLBACK_LOGO = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
    "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
)

# Student section for generating contract definition
USER_FALLBACK_ADDRESS = {
    "address": _("<STUDENT_ADDRESS_STREET_NAME>"),
    "city": _("<STUDENT_ADDRESS_CITY>"),
    "country": _("<STUDENT_ADDRESS_COUNTRY>"),
    "last_name": _("<STUDENT_LAST_NAME>"),
    "first_name": _("<STUDENT_FIRST_NAME>"),
    "postcode": _("<STUDENT_ADDRESS_POSTCODE>"),
    "title": _("<STUDENT_ADDRESS_TITLE>"),
    "is_main": True,
}


def apply_contract_definition_context_processors(context):
    """
    Apply all the context processors for contract definition.

    This method will apply all the context processors for contract definition
    and return the updated context.
    """
    context = context.copy()

    for path in settings.JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS[
        "contract_definition"
    ]:
        processor = import_string(path)
        context.update(processor(context))

    return context


# ruff: noqa: PLR0912, PLR0915
# pylint: disable=import-outside-toplevel, too-many-locals, too-many-statements
def generate_document_context(contract_definition=None, user=None, order=None):
    """
    Generate a document context for a contract definition.

    This method requires a contract definition object and a user object.
    The order or the user's address are optional, we handle them by replacing their values
    with defaults placeholder.
    We can use this method to preview a contract definition, or to generate its context when all
    the parameters are set.
    """
    # pylint: disable=cyclic-import
    from joanie.core.models import Address
    from joanie.core.serializers.client import AddressSerializer

    contract_language = (
        contract_definition.language if contract_definition else settings.LANGUAGE_CODE
    )

    organization_logo_id = None
    organization_name = _("<ORGANIZATION_NAME>")
    organization_representative = _("<REPRESENTATIVE>")
    organization_representative_profession = _("<REPRESENTATIVE_PROFESSION>")
    organization_enterprise_code = _("<ENTERPRISE_CODE>")
    organization_activity_category_code = _("<ACTIVITY_CATEGORY_CODE>")
    organization_signatory_representative = _("<SIGNATORY_REPRESENTATIVE>")
    organization_signatory_profession = _("<SIGNATURE_REPRESENTATIVE_PROFESSION>")
    organization_contact_phone = _("<CONTACT_PHONE>")
    organization_contact_email = _("<CONTACT_EMAIL>")
    organization_dpo_email = _("<DPO_EMAIL_ADDRESS>")
    organization_address = ORGANIZATION_FALLBACK_ADDRESS

    course_code = _("<COURSE_CODE>")
    course_name = _("<COURSE_NAME>")
    course_start = _("<COURSE_START_DATE>")
    course_end = _("<COURSE_END_DATE>")
    course_effort = _("<COURSE_EFFORT>")
    course_price = _("<COURSE_PRICE>")

    user_name = _("<STUDENT_NAME>")
    user_email = _("<STUDENT_EMAIL>")
    user_phone_number = _("<STUDENT_PHONE_NUMBER>")
    user_address = USER_FALLBACK_ADDRESS

    contract_body = _("<CONTRACT_BODY>")
    contract_title = _("<CONTRACT_TITLE>")
    contract_description = _("<CONTRACT_DESCRIPTION>")

    if contract_definition:
        contract_body = contract_definition.get_body_in_html()
        contract_title = contract_definition.title
        contract_description = contract_definition.description

    if user:
        user_name = user.get_full_name() or user.username
        user_email = user.email
        user_phone_number = user.phone_number

    if order:
        logo_checksum = file_checksum(order.organization.logo)
        logo_image, created = DocumentImage.objects.get_or_create(
            checksum=logo_checksum,
            defaults={"file": order.organization.logo},
        )
        if created:
            contract_definition.images.set([logo_image])
        organization_logo_id = str(logo_image.id)

        organization_name = order.organization.safe_translation_getter(
            "title", language_code=contract_language
        )
        organization_representative = order.organization.representative
        organization_representative_profession = (
            order.organization.representative_profession
        )
        organization_enterprise_code = order.organization.enterprise_code
        organization_activity_category_code = order.organization.activity_category_code
        organization_signatory_representative = (
            order.organization.signatory_representative
        )
        organization_signatory_profession = (
            order.organization.signatory_representative_profession
        )
        organization_contact_phone = order.organization.contact_phone
        organization_contact_email = order.organization.contact_email
        organization_dpo_email = order.organization.dpo_email

        try:
            organization_address = order.organization.addresses.get(is_main=True)
        except Address.DoesNotExist:
            organization_address = None

        # Course
        course_code = order.course.code
        course_name = order.product.safe_translation_getter(
            "title", language_code=contract_language
        )
        course_dates = order.get_equivalent_course_run_dates()
        course_start = course_dates["start"]
        course_end = course_dates["end"]
        course_effort = order.course.effort
        course_price = str(order.total)
        user_address = order.main_invoice.recipient_address

    # Transform duration value to ISO 8601 format
    if isinstance(course_effort, timedelta):
        course_effort = duration_iso_string(course_effort)
    # Transform date value to ISO 8601 format
    if isinstance(course_start, date):
        course_start = course_start.isoformat()
    if isinstance(course_end, date):
        course_end = course_end.isoformat()

    if organization_address:
        organization_address = AddressSerializer(organization_address).data

    if user_address:
        user_address = AddressSerializer(user_address).data

    context = {
        "contract": {
            "title": contract_title,
            "description": contract_description,
            "body": contract_body,
            "language": contract_language,
        },
        "course": {
            "name": course_name,
            "code": course_code,
            "start": course_start,
            "end": course_end,
            "effort": course_effort,
            "price": course_price,
            "currency": get_currency_symbol(settings.DEFAULT_CURRENCY),
        },
        "student": {
            "address": user_address,
            "name": user_name,
            "email": user_email,
            "phone_number": user_phone_number,
        },
        "organization": {
            "address": organization_address,
            "logo_id": organization_logo_id,
            "name": organization_name,
            "representative": organization_representative,
            "representative_profession": organization_representative_profession,
            "enterprise_code": organization_enterprise_code,
            "activity_category_code": organization_activity_category_code,
            "signatory_representative": organization_signatory_representative,
            "signatory_representative_profession": organization_signatory_profession,
            "contact_phone": organization_contact_phone,
            "contact_email": organization_contact_email,
            "dpo_email": organization_dpo_email,
        },
    }

    return apply_contract_definition_context_processors(context)


def embed_images_in_context(context):
    """Embed images in the context."""
    edited_context = deepcopy(context)
    try:
        logo = DocumentImage.objects.get(id=edited_context["organization"]["logo_id"])
        edited_context["organization"]["logo"] = image_to_base64(logo.file)
    except DocumentImage.DoesNotExist:
        edited_context["organization"]["logo"] = ORGANIZATION_FALLBACK_LOGO

    del edited_context["organization"]["logo_id"]
    return edited_context
