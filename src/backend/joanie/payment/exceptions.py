"""Payment exceptions"""

from http import HTTPStatus

from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException


class AbortPaymentFailed(APIException):
    """Exception triggered when aborting a payment failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot abort this payment.")
    default_code = "abort_payment_failed"


class CreatePaymentFailed(APIException):
    """Exception triggered when creating payment failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot create a payment.")
    default_code = "create_payment_failed"


class RegisterPaymentFailed(APIException):
    """Exception triggered when registering payment failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot register this payment.")
    default_code = "register_payment_failed"


class TokenizationCardFailed(APIException):
    """Exception triggered when registering payment failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot register this payment.")
    default_code = "register_payment_failed"


class RefundPaymentFailed(APIException):
    """Exception triggered when refunding payment failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot refund this payment.")
    default_code = "refund_payment_failed"


class ParseNotificationFailed(APIException):
    """Exception triggered when parsing notification failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot parse notification.")
    default_code = "parse_notification_failed"


class PaymentProviderAPIException(APIException):
    """Exception triggered when the payment provider API to create payment failed"""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Payment provider API error.")
    default_code = "payment_provider_api_error"


class PaymentProviderAPIServerException(APIException):
    """Exception triggered when the payment provider API server call failed"""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    default_detail = _("Payment provider API server error.")
    default_code = "payment_provider_api_server_error"
