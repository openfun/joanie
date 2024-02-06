"""Utility to `generate document context` data"""
from django.contrib.sites.models import Site
from django.utils.translation import gettext as _

from joanie.core.utils import image_to_base64


# pylint: disable=import-outside-toplevel
def generate_document_context(contract_definition, user, order=None):
    """
    Generate a document context for a contract definition.

    This method requires a contract definition object and a user object.
    The order or the user's address are optional, we handle them by replacing their values
    with defaults placeholder.
    We can use this method to preview a contract definition, or to generate its context when all
    the parameters are set.
    """
    from joanie.core.serializers.client import (  # pylint: disable=cyclic-import
        AddressSerializer,
    )

    organization_fallback_logo = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
        "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
    )

    fallback_address = {
        "address": _("<STUDENT_ADDRESS_STREET_NAME>"),
        "city": _("<STUDENT_ADDRESS_CITY>"),
        "country": _("<STUDENT_ADDRESS_COUNTRY>"),
        "last_name": _("<STUDENT_LAST_NAME>"),
        "first_name": _("<STUDENT_FIRST_NAME>"),
        "postcode": _("<STUDENT_ADDRESS_POSTCODE>"),
        "title": "",
    }

    user_address = order.main_invoice.recipient_address if order else fallback_address

    address = AddressSerializer(user_address).data

    try:
        site_config = Site.objects.get_current().site_config
    except Site.site_config.RelatedObjectDoesNotExist:  # pylint: disable=no-member
        terms_and_conditions = ""
    else:
        terms_and_conditions = site_config.get_terms_and_conditions_in_html(
            contract_definition.language
        )

    return {
        "contract": {
            "body": contract_definition.get_body_in_html(),
            "terms_and_conditions": terms_and_conditions,
            "title": contract_definition.title,
        },
        "course": {
            "name": (
                order.product.safe_translation_getter(
                    "title", language_code=contract_definition.language
                )
                if order
                else _("<COURSE_NAME>")
            )
        },
        "student": {"name": user.get_full_name() or user.username, "address": address},
        "organization": {
            "logo": (
                image_to_base64(order.organization.logo)
                if order
                else organization_fallback_logo
            ),
            "name": (
                order.organization.safe_translation_getter(
                    "title", language_code=contract_definition.language
                )
                if order
                else _("<ORGANIZATION_NAME>")
            ),
        },
    }
