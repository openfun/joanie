"""Util to manage the deletion of Order depending the state and the product type"""

from uuid import UUID

from joanie.core import enums, models


def delete_stuck_signing_order(order: models.Order):
    """
    Delete related objects and the Order itself when it is stuck in signing states.
    This method handles orders in the `ORDER_STATE_TO_SIGN` or `ORDER_STATE_SIGNING` states,
    which occur when users abandon the signing process in the sales tunnel.
    These states indicate that the order required a signature on the contract but was never
    completed by the user.
    """
    if order.state not in [enums.ORDER_STATE_TO_SIGN, enums.ORDER_STATE_SIGNING]:
        return
    order.contract.delete()
    order.main_invoice.delete()
    order.delete()


def delete_stuck_certificate_order(order: models.Order):
    """
    Delete related objects and the Order itself when it is stuck for a product type certificate
    in the state `ORDER_STATE_TO_SAVE_PAYMENT_METHOD`.
    These orders are created when a user starts but does not complete the payment process
    for a certificate.
    """
    if order.state not in [
        enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD
    ] or order.product.type in [
        enums.PRODUCT_TYPE_ENROLLMENT,
        enums.PRODUCT_TYPE_CREDENTIAL,
    ]:
        return
    order.main_invoice.delete()
    order.delete()


def delete_stuck_orders():
    """
    Delete all the orders that are considered as stuck.
    For products with contract, it's all the orders that are stuck in signing states.
    For product with certificate, it's all the order that are stuck in to save payment method.
    """
    deleted_orders_in_signing_states = 0
    deleted_orders_in_to_save_payment_state = 0

    for order in models.Order.objects.get_stuck_signing_orders():
        delete_stuck_signing_order(order)
        deleted_orders_in_signing_states += 1

    for order in models.Order.objects.get_stuck_certificate_payment_orders():
        delete_stuck_certificate_order(order)
        deleted_orders_in_to_save_payment_state += 1

    return deleted_orders_in_signing_states, deleted_orders_in_to_save_payment_state


def verify_voucher(voucher_code: str) -> models.Voucher | None:
    """
    When a voucher code is used to create an order, we will verify if it exists and whether it's
    active to be consumed. If the object is found, we return it, else we return None.
    """
    voucher = models.Voucher.objects.filter(
        code__iexact=voucher_code, is_active=True
    ).first()
    if not voucher:
        return None
    return voucher


def get_prepaid_order(
    course_code: str, product_id: UUID, voucher_code: str
) -> models.Order | None:
    """
    When an eligible voucher code is used to create an order, we will verify if it can be used
    with the course and product relation passed. If we find the order in state `to_own` that
    matches the information, we return it, else we return None.
    """
    try:
        return models.Order.objects.get(
            course__code=course_code,
            product_id=product_id,
            voucher__code=voucher_code,
            voucher__discount__rate=1,
            state=enums.ORDER_STATE_TO_OWN,
        )
    except models.Order.DoesNotExist:
        return None
