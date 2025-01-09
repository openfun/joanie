"""
The check defined here is registered with Django's system check framework.
It ensures and informs developers that some fields of payment models will be soon deprecated,
and we provide guidance for transition.

You can use our make command : `make check`
This message will also appear when using : `make migrate`

https://docs.djangoproject.com/fr/4.2/topics/checks/
"""

from django.apps import apps
from django.core.checks import Warning as django_check_message_warning
from django.core.checks import register


@register()
def check_deprecated_owner_field(app_configs, **kwargs):  # pylint: disable=unused-argument
    """
    Warning developers that the field `owner` and `is_main` on the CreditCard model are deprecated
    and they will be removed in a couple of future release of Joanie higher than 2.15.0
    """
    warnings = []

    CreditCard = apps.get_model("payment", "CreditCard")  # pylint: disable=invalid-name

    deprecated_fields = {
        "owner": {
            "message": (
                "'owner' has been deprecated on the CreditCard model in the payment app. "
                "Support for it (except in historical migrations) will be removed in a future "
                "release of Joanie higher than 2.15.0."
            ),
            "hint": "Use 'owners' many-to-many relation instead.",
            "id": "credit_card.owner",
        },
        "is_main": {
            "message": (
                "'is_main' has been deprecated on the CreditCard model in the payment app. "
                "Support for it (except in historical migrations) will be removed in a future "
                "release of Joanie higher than 2.15.0."
            ),
            "hint": "Use 'is_main' on the CreditCardOwnership model to manage it per user.",
            "id": "credit_card.is_main",
        },
    }

    card_fields = [field.name for field in CreditCard._meta.get_fields()]  # noqa: SLF001
    for field_name, details in deprecated_fields.items():
        if field_name in card_fields:
            warnings.append(
                django_check_message_warning(
                    msg=details["message"],
                    hint=details["hint"],
                    id=details["id"],
                    obj="CreditCard",
                )
            )

    return warnings
