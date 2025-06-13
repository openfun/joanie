"""Utils for Batch Order"""

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from joanie.core import models
from joanie.core.utils.emails import send
from joanie.core.utils.organization import get_least_active_organization
from joanie.payment import get_payment_backend
from joanie.payment.models import Invoice, Transaction


def get_active_offer_rule(relation_id, nb_seats: int):
    """
    Responsible to seek for an active offer rule where the number of seats is available.
    Otherwise, if all active offer rules don't have enough seats requested, it raises an error.
    When no offer rules is found for the relation, it returns None.
    """
    offer_rules = models.OfferRule.objects.find_actives(
        course_product_relation_id=relation_id
    )
    seats_limitation = None
    for offer_rule in offer_rules:
        if offer_rule.nb_seats is not None:
            if offer_rule.available_seats < nb_seats:
                seats_limitation = offer_rule
                continue

            seats_limitation = None

        if offer_rule.is_enabled:
            return offer_rule

    if seats_limitation:
        raise ValueError(_("Seat limitation has been reached."))

    # No offer rules were setted for this relation
    return None


def assign_organization(batch_order):
    """
    Assigns an organization to a batch order with the least active orders.
    It also add an active offer rule if some are declared on the course product relation.
    Finally, it initiates the flow of the batch order to state 'assigned'.
    """
    batch_order.organization = get_least_active_organization(
        batch_order.relation.product, batch_order.relation.course
    )

    offer_rule = get_active_offer_rule(
        relation_id=batch_order.relation.id, nb_seats=batch_order.nb_seats
    )
    if offer_rule:
        batch_order.offer_rules.add(offer_rule)

    batch_order.init_flow()


def send_mail_invitation_link(batch_order, invitation_link: str):
    """
    Sends an email to the batch order owner with the link to sign the contract
    into the owner's language.
    """
    with override(batch_order.owner.language):
        product_title = batch_order.relation.product.safe_translation_getter(
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


def send_mail_vouchers(batch_order):
    """Send an email to batch order's owner with vouchers into the owner's language."""

    payment_backend = get_payment_backend()
    # pylint:disable=protected-access
    payment_backend._send_mail_batch_order_payment_success(  # noqa: SLF001
        batch_order, batch_order.total, batch_order.vouchers
    )
