"""Utility to `generate document context` data"""

from copy import deepcopy
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.duration import duration_iso_string
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from joanie.core.models import DocumentImage
from joanie.core.utils import (
    file_checksum,
    get_default_currency_symbol,
    image_to_base64,
)
from joanie.core.utils.payment_schedule import generate as generate_payment_schedule

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


def prepare_organization_context(
    language_code, contract_definition, order=None, batch_order=None
):
    """Prepare organization context for the document generation."""
    # pylint: disable=cyclic-import, import-outside-toplevel
    from joanie.core.models import Address
    from joanie.core.serializers.client import AddressSerializer

    organization_context = {
        "address": ORGANIZATION_FALLBACK_ADDRESS,
        "logo_id": None,
        "name": _("<ORGANIZATION_NAME>"),
        "representative": _("<REPRESENTATIVE>"),
        "representative_profession": _("<REPRESENTATIVE_PROFESSION>"),
        "enterprise_code": _("<ENTERPRISE_CODE>"),
        "activity_category_code": _("<ACTIVITY_CATEGORY_CODE>"),
        "signatory_representative": _("<SIGNATORY_REPRESENTATIVE>"),
        "signatory_representative_profession": _(
            "<SIGNATURE_REPRESENTATIVE_PROFESSION>"
        ),
        "contact_phone": _("<CONTACT_PHONE>"),
        "contact_email": _("<CONTACT_EMAIL>"),
        "dpo_email": _("<DPO_EMAIL_ADDRESS>"),
    }

    if order or batch_order:
        organization = order.organization if order else batch_order.organization
        logo_checksum = file_checksum(organization.logo)
        logo_image, created = DocumentImage.objects.get_or_create(
            checksum=logo_checksum,
            defaults={"file": organization.logo},
        )
        if created:
            contract_definition.images.set([logo_image])
        organization_logo_id = str(logo_image.id)

        try:
            organization_address = organization.addresses.get(is_main=True)
        except Address.DoesNotExist:
            organization_address = None
        if organization_address:
            organization_address = AddressSerializer(organization_address).data

        organization_context.update(
            {
                "address": organization_address,
                "logo_id": organization_logo_id,
                "name": organization.safe_translation_getter(
                    "title", language_code=language_code
                ),
                "representative": organization.representative,
                "representative_profession": organization.representative_profession,
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": organization.activity_category_code,
                "signatory_representative": organization.signatory_representative,
                "signatory_representative_profession": (
                    organization.signatory_representative_profession
                ),
                "contact_phone": organization.contact_phone,
                "contact_email": organization.contact_email,
                "dpo_email": organization.dpo_email,
            }
        )

    return organization_context


def prepare_course_context(language_code, order=None):
    """Prepare course context for the document generation"""
    course_context = {
        "name": _("<COURSE_NAME>"),
        "code": _("<COURSE_CODE>"),
        "start": _("<COURSE_START_DATE>"),
        "end": _("<COURSE_END_DATE>"),
        "effort": _("<COURSE_EFFORT>"),
        "price": _("<COURSE_PRICE>"),
        "currency": get_default_currency_symbol(),
    }

    if order:
        course_dates = order.get_equivalent_course_run_dates()
        course_start = course_dates["start"]
        course_end = course_dates["end"]
        course_effort = order.course.effort
        # Transform duration value to ISO 8601 format
        if isinstance(course_effort, timedelta):
            course_effort = duration_iso_string(course_effort)
        # Transform date value to ISO 8601 format
        if isinstance(course_start, date):
            course_start = course_start.isoformat()
        if isinstance(course_end, date):
            course_end = course_end.isoformat()

        course_context.update(
            {
                "name": order.product.safe_translation_getter(
                    "title", language_code=language_code
                ),
                "code": order.course.code,
                "start": course_start,
                "end": course_end,
                "effort": course_effort,
                "price": str(order.total),
            }
        )

    return course_context


def prepare_student_context(user):
    """
    Prepare student context for document generation.
    """
    student_context = {
        "address": USER_FALLBACK_ADDRESS,
        "name": _("<STUDENT_NAME>"),
        "email": _("<STUDENT_EMAIL>"),
        "phone_number": _("<STUDENT_PHONE_NUMBER>"),
        "payment_schedule": None,
    }

    if user:
        student_context.update(
            {
                "name": user.name,
                "email": user.email,
                "phone_number": user.phone_number,
            }
        )

    return student_context


def prepare_contract_definition_context(language_code, contract_definition):
    """
    Prepare contract definition context for document generation.
    """
    contract_definition_context = {
        "title": _("<CONTRACT_TITLE>"),
        "description": _("<CONTRACT_DESCRIPTION>"),
        "body": _("&lt;CONTRACT_BODY&gt;"),
        "appendix": _("&lt;CONTRACT_APPENDIX&gt;"),
        "language": language_code,
    }

    if contract_definition:
        contract_definition_context.update(
            {
                "title": contract_definition.title,
                "description": contract_definition.description,
                "body": contract_definition.get_body_in_html(),
                "appendix": contract_definition.get_appendix_in_html(),
            }
        )

    return contract_definition_context


def prepare_company_context(batch_order):
    """Prepare batch order company informations for document generation"""
    company_context = {
        "name": _("<COMPANY_NAME>"),
        "address": _("<COMPANY_ADDRESS>"),
        "post_code": _("<COMPANY_POSTCODE>"),
        "city": _("<COMPANY_CITY>"),
        "identification_number": _("<COMPANY_IDENTIFICATION_NUMBER>"),
        "number_seats": _("<NUMBER_OF_SEATS_RESERVED>"),
    }

    if batch_order:
        company_context.update(
            {
                "name": batch_order.company_name,
                "address": batch_order.address,
                "postcode": batch_order.postcode,
                "city": batch_order.city,
                "identification_number": batch_order.identification_number,
                "number_seats": batch_order.nb_seats,
            }
        )

    return company_context


# ruff: noqa: PLR0912, PLR0915
# pylint: disable=import-outside-toplevel, too-many-locals, too-many-statements, too-many-branches
def generate_document_context(
    contract_definition=None, user=None, order=None, batch_order=None
):
    """
    Generate a document context for a contract definition.

    This method requires a contract definition object and a user object.
    The order or the user's address are optional, we handle them by replacing their values
    with defaults placeholder.
    We can use this method to preview a contract definition, or to generate its context when all
    the parameters are set.
    """
    # pylint: disable=cyclic-import
    from joanie.core.serializers.client import AddressSerializer

    contract_language = (
        contract_definition.language if contract_definition else settings.LANGUAGE_CODE
    )

    organization_context = prepare_organization_context(
        language_code=contract_language,
        contract_definition=contract_definition,
        order=order,
        batch_order=batch_order,
    )
    course_context = prepare_course_context(
        language_code=contract_language, order=order
    )
    student_context = prepare_student_context(user=user)
    contract_context = prepare_contract_definition_context(
        language_code=contract_language, contract_definition=contract_definition
    )
    company_context = prepare_company_context(batch_order=batch_order)

    if order:
        user_address = order.main_invoice.recipient_address
        user_address = AddressSerializer(user_address).data
        student_context.update({"address": user_address})
        # Payment Schedule
        try:
            beginning_contract_date, course_start_date, course_end_date = (
                order.get_schedule_dates()
            )
        except ValidationError:
            pass
        else:
            installments = generate_payment_schedule(
                order.total,
                beginning_contract_date,
                course_start_date,
                course_end_date,
            )
            payment_schedule = [
                {
                    "due_date": installment["due_date"].isoformat(),
                    "amount": str(installment["amount"]),
                }
                for installment in installments
            ]
            student_context.update({"payment_schedule": payment_schedule})

    context = {
        "contract": contract_context,
        "course": course_context,
        "student": student_context,
        "organization": organization_context,
        "company": company_context,
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
