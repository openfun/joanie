"""Utils for Batch Order"""

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from joanie.core import models
from joanie.core.utils.emails import send
from joanie.core.utils.organization import get_least_active_organization
from joanie.payment.models import Invoice, Transaction


def get_active_offering_rule(offering_id, nb_seats: int):
    """
    Responsible to seek for an active offering rule where the number of seats is available.
    Otherwise, if all active offering rules don't have enough seats requested, it raises an error.
    When no offering rules is found for the offering, it returns None.
    """
    offering_rules = models.OfferingRule.objects.find_actives(offering_id=offering_id)
    seats_limitation = None
    for offering_rule in offering_rules:
        if offering_rule.nb_seats is not None:
            if offering_rule.available_seats < nb_seats:
                seats_limitation = offering_rule
                continue

            seats_limitation = None

        if offering_rule.is_enabled:
            return offering_rule

    if seats_limitation:
        raise ValueError(_("Seat limitation has been reached."))

    # No offering rules were set for this offering
    return None


def assign_organization(batch_order):
    """
    Assigns an organization to a batch order with the least active orders.
    It also adds an active offering rule if some are declared on the offering.
    Finally, it initiates the flow of the batch order to state 'quoted'.
    """
    batch_order.organization = get_least_active_organization(
        batch_order.offering.product, batch_order.offering.course
    )

    offering_rule = get_active_offering_rule(
        offering_id=batch_order.offering.id, nb_seats=batch_order.nb_seats
    )
    if offering_rule:
        batch_order.offering_rules.add(offering_rule)

    batch_order.init_flow()


def send_mail_invitation_link(batch_order, invitation_link: str):
    """
    Sends an email to the batch order owner with the link to sign the contract
    into the owner's language.
    """
    with override(batch_order.owner.language):
        product_title = batch_order.offering.product.safe_translation_getter(
            "title", language_code=batch_order.owner.language
        )
        send(
            subject=_(
                f"{product_title} - A signature is requested for your batch order."
            ),
            template_vars={
                "title": _(
                    f"{product_title} - A signature is requested for your batch order."
                ),
                "email": batch_order.owner.email,
                "fullname": batch_order.owner.get_full_name(),
                "product_title": product_title,
                "invitation_link": invitation_link,
                "site": {
                    "name": settings.JOANIE_CATALOG_NAME,
                    "url": settings.JOANIE_CATALOG_BASE_URL,
                },
            },
            template_name="invitation_to_sign_contract",
            to_user_email=batch_order.owner.email,
        )


def validate_success_payment(batch_order):
    """
    Creates the invoice and the transaction of the successful payment.
    Finally, it updates the state to 'completed'.
    """
    invoice = Invoice.objects.create(
        batch_order=batch_order,
        parent=batch_order.main_invoice,
        total=0,
    )
    # Store the payment transaction
    Transaction.objects.create(
        total=batch_order.total,
        invoice=invoice,
        reference=f"bo_{batch_order.id}",
    )

    # Transition to `completed` state
    batch_order.flow.update()
