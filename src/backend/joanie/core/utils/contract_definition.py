"""Utility to `generate document context` data"""
from django.contrib.sites.models import Site
from django.utils.translation import gettext as _

from joanie.core.utils import image_to_base64

# Organization section for generating contract definition
ORGANIZATION_FALLBACK_ADDRESS = {
    "address": _("<ORGANIZATION_ADDRESS_STREET_NAME>"),
    "city": _("<ORGANIZATION_ADDRESS_CITY>"),
    "country": _("<ORGANIZATION_ADDRESS_COUNTRY>"),
    "last_name": _("<ORGANIZATION_LAST_NAME>"),
    "first_name": _("<ORGANIZATION_FIRST_NAME>"),
    "postcode": _("<ORGANIZATION_ADDRESS_POSTCODE>"),
    "title": _("<ORGANIZATION_ADDRESS_TITLE>"),
}

# Student section for generating contract definition
USER_FALLBACK_ADDRESS = {
    "address": _("<STUDENT_ADDRESS_STREET_NAME>"),
    "city": _("<STUDENT_ADDRESS_CITY>"),
    "country": _("<STUDENT_ADDRESS_COUNTRY>"),
    "last_name": _("<STUDENT_LAST_NAME>"),
    "first_name": _("<STUDENT_FIRST_NAME>"),
    "postcode": _("<STUDENT_ADDRESS_POSTCODE>"),
    "title": _("<STUDENT_ADDRESS_TITLE>"),
}


# ruff: noqa: PLR0915
# pylint: disable=import-outside-toplevel, too-many-locals, too-many-statements
def generate_document_context(contract_definition, user, order=None):
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

    organization_fallback_logo = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
        "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
    )

    try:
        site_config = Site.objects.get_current().site_config
    except Site.site_config.RelatedObjectDoesNotExist:  # pylint: disable=no-member
        terms_and_conditions = ""
    else:
        terms_and_conditions = site_config.get_terms_and_conditions_in_html(
            contract_definition.language
        )

    organization_logo = organization_fallback_logo
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
    course_price = _("<PRICE>")

    user_address = USER_FALLBACK_ADDRESS

    if order:
        organization_logo = image_to_base64(order.organization.logo)
        organization_name = order.organization.safe_translation_getter(
            "title", language_code=contract_definition.language
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
            organization_address = ORGANIZATION_FALLBACK_ADDRESS

        # Course
        course_code = order.course.code
        course_name = order.product.safe_translation_getter(
            "title", language_code=contract_definition.language
        )
        course_dates = order.get_equivalent_course_run_dates()
        course_start = course_dates["start"]
        course_end = course_dates["end"]
        course_price = str(order.total)

        user_address = order.main_invoice.recipient_address

    address_organization = AddressSerializer(organization_address).data
    address_user = AddressSerializer(user_address).data

    return {
        "contract": {
            "body": contract_definition.get_body_in_html(),
            "terms_and_conditions": terms_and_conditions,
            "title": contract_definition.title,
        },
        "course": {
            "name": course_name,
            "code": course_code,
            "start": course_start,
            "end": course_end,
            "effort": None,
            "price": course_price,
        },
        "student": {
            "address": address_user,
            "name": user.get_full_name() or user.username,
            "email": (user.email if user else _("<USER_EMAIL>")),
            "phone_number": None,
        },
        "organization": {
            "address": address_organization,
            "logo": organization_logo,
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
