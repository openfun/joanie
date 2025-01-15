"""
The check defined here is registered with Django's system check framework.
It ensures and informs developers that some field of a model will be soon deprecated, and we
provide guidance for transition. It warns that it will be removed in a couple of releases.

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
    Warning developers that the field `owner` is deprecated and will be removed in a couple of
    future release of Joanie higher than 2.13.0
    """
    warnings = []

    CreditCard = apps.get_model("payment", "CreditCard")  # pylint: disable=invalid-name
    if "owner" in [field.name for field in CreditCard._meta.get_fields()]:  # noqa: SLF001
        warnings.append(
            django_check_message_warning(
                "'owner' has been deprecated on the CreditCard model in the payment app. "
                "Support for it (except in historical migrations) will be removed future release "
                "of Joanie higher 2.13.0",
                hint="Use 'owners' many-to-many relation instead.",
                id="fields.credit_card.owner",
            )
        )

    return warnings
