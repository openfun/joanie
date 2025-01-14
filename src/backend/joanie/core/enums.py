"""
Core application enums declaration
"""

from django.conf import global_settings, settings
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

# Roles
OWNER = "owner"
ADMIN = "administrator"
INSTRUCTOR = "instructor"
MANAGER = "manager"
MEMBER = "member"

# Django sets `LANGUAGES` by default with all supported languages. We can use it for example for
# the choice of languages on the course run which should not be limited to the few languages
# active in the app.
# pylint: disable=no-member
ALL_LANGUAGES = getattr(
    settings,
    "ALL_LANGUAGES",
    [(language, _(name)) for language, name in global_settings.LANGUAGES],
)

PRODUCT_TYPE_CREDENTIAL = "credential"
PRODUCT_TYPE_ENROLLMENT = "enrollment"
PRODUCT_TYPE_CERTIFICATE = "certificate"

PRODUCT_TYPE_CHOICES = (
    # user purchases all (enrollments + certificate) from the start
    (PRODUCT_TYPE_CREDENTIAL, _("Credential")),
    # user is just enrolled in course runs (for free or not)
    (PRODUCT_TYPE_ENROLLMENT, _("Enrollment")),
    # user is enrolled in course runs for free
    # finally orchestrator will offer user to pay to get a certificate
    (PRODUCT_TYPE_CERTIFICATE, _("Certificate")),
)
PRODUCT_TYPE_ORDER_FIELDS = {
    # product type            required | empty
    PRODUCT_TYPE_CREDENTIAL: ("course", "enrollment"),
    PRODUCT_TYPE_ENROLLMENT: ("course", "enrollment"),
    PRODUCT_TYPE_CERTIFICATE: ("enrollment", "course"),
}

PRODUCT_TYPE_CERTIFICATE_ALLOWED = [
    PRODUCT_TYPE_CERTIFICATE,
    PRODUCT_TYPE_CREDENTIAL,
]

COURSE_AND_SEARCH = "course_and_search"
COURSE_ONLY = "course_only"
HIDDEN = "hidden"
CATALOG_VISIBILITY_CHOICES = (
    COURSE_AND_SEARCH,
    COURSE_ONLY,
    HIDDEN,
)

ORDER_STATE_DRAFT = "draft"  # order has been created
ORDER_STATE_ASSIGNED = "assigned"  # order has been assigned to an organization
ORDER_STATE_TO_SAVE_PAYMENT_METHOD = (
    "to_save_payment_method"  # order needs a payment method
)
ORDER_STATE_TO_SIGN = "to_sign"  # order needs a contract signature
ORDER_STATE_SIGNING = "signing"  # order is being signed
ORDER_STATE_PENDING = "pending"  # payment has failed but can be retried
ORDER_STATE_CANCELED = "canceled"  # has been canceled
ORDER_STATE_PENDING_PAYMENT = "pending_payment"  # payment is pending
ORDER_STATE_FAILED_PAYMENT = "failed_payment"  # last payment has failed
ORDER_STATE_NO_PAYMENT = "no_payment"  # no payment has been made
ORDER_STATE_COMPLETED = "completed"  # is completed
ORDER_STATE_REFUNDING = "refunding"  # order is being reimbursed
ORDER_STATE_REFUNDED = "refunded"  # order installment payments are refunded

ORDER_STATE_CHOICES = (
    (ORDER_STATE_DRAFT, _("Draft")),  # default
    (ORDER_STATE_ASSIGNED, _("Assigned")),
    (ORDER_STATE_TO_SAVE_PAYMENT_METHOD, _("To save payment method")),
    (ORDER_STATE_TO_SIGN, _("To sign")),
    (ORDER_STATE_SIGNING, _("Signing")),
    (ORDER_STATE_PENDING, _("Pending")),
    (ORDER_STATE_CANCELED, pgettext_lazy("As in: the order is canceled.", "Canceled")),
    (
        ORDER_STATE_PENDING_PAYMENT,
        pgettext_lazy("As in: the order payment is pending.", "Pending payment"),
    ),
    (
        ORDER_STATE_FAILED_PAYMENT,
        pgettext_lazy("As in: the last order payment has failed.", "Failed payment"),
    ),
    (
        ORDER_STATE_NO_PAYMENT,
        pgettext_lazy("As in: the first order payment has failed.", "No payment"),
    ),
    (
        ORDER_STATE_COMPLETED,
        pgettext_lazy("As in: the order is completed.", "Completed"),
    ),
    (
        ORDER_STATE_REFUNDING,
        pgettext_lazy("As in: the order is being refunded", "Refunding"),
    ),
    (
        ORDER_STATE_REFUNDED,
        pgettext_lazy("As in: the order payments are refunded", "Refunded"),
    ),
)
ORDER_STATE_ALLOW_ENROLLMENT = (
    ORDER_STATE_COMPLETED,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_FAILED_PAYMENT,
)
ORDER_STATES_BINDING = (
    *ORDER_STATE_ALLOW_ENROLLMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_NO_PAYMENT,
)
MIN_ORDER_TOTAL_AMOUNT = 0.0
ORDER_INACTIVE_STATES = (
    ORDER_STATE_CANCELED,
    ORDER_STATE_REFUNDING,
    ORDER_STATE_REFUNDED,
)

ENROLLMENT_STATE_SET = "set"
ENROLLMENT_STATE_FAILED = "failed"
ENROLLMENT_STATE_PASSED = "passed"

ENROLLMENT_STATE_CHOICES = (
    (
        ENROLLMENT_STATE_SET,
        pgettext_lazy("As in: the enrollment was successfully set on the LMS.", "Set"),
    ),
    (
        ENROLLMENT_STATE_FAILED,
        pgettext_lazy("As in: the enrollment failed on the LMS.", "Failed"),
    ),
)

# For contract names choices
CONTRACT_DEFINITION_DEFAULT = "contract_definition_default"
CONTRACT_DEFINITION_UNICAMP = "contract_definition_unicamp"

CONTRACT_NAME_CHOICES = (
    (CONTRACT_DEFINITION_DEFAULT, _("Contract Definition Default")),
    (CONTRACT_DEFINITION_UNICAMP, _("Contract Definition Unicamp")),
)

# For contract signature state choices
CONTRACT_SIGNATURE_STATE_UNSIGNED = "unsigned"
CONTRACT_SIGNATURE_STATE_HALF_SIGNED = "half_signed"
CONTRACT_SIGNATURE_STATE_SIGNED = "signed"

CONTRACT_SIGNATURE_STATE_FILTER_CHOICES = (
    (CONTRACT_SIGNATURE_STATE_UNSIGNED, _("Unsigned")),
    (
        CONTRACT_SIGNATURE_STATE_HALF_SIGNED,
        _("Partially signed"),
    ),  # Only the student has signed, organization is pending
    (CONTRACT_SIGNATURE_STATE_SIGNED, _("Signed")),
)

# For certification names choices
CERTIFICATE = "certificate"
DEGREE = "degree"
UNICAMP_DEGREE = "unicamp-degree"

VERIFIABLE_CERTIFICATES = (DEGREE, UNICAMP_DEGREE)

CERTIFICATE_NAME_CHOICES = (
    (CERTIFICATE, _("Certificate")),
    (DEGREE, _("Degree")),
    (UNICAMP_DEGREE, _("Unicamp degree")),
)

# For filtering certificates by type
CERTIFICATE_ORDER_TYPE = "order"
CERTIFICATE_ENROLLMENT_TYPE = "enrollment"
CERTIFICATE_TYPE_CHOICES = (
    (CERTIFICATE_ORDER_TYPE, _("Order")),
    (CERTIFICATE_ENROLLMENT_TYPE, _("Enrollment")),
)

# For activity log level choices
ACTIVITY_LOG_LEVEL_INFO = "info"
ACTIVITY_LOG_LEVEL_SUCCESS = "success"
ACTIVITY_LOG_LEVEL_WARNING = "warning"
ACTIVITY_LOG_LEVEL_ERROR = "error"

ACTIVITY_LOG_LEVEL_CHOICES = (
    (ACTIVITY_LOG_LEVEL_INFO, _("Info")),
    (ACTIVITY_LOG_LEVEL_SUCCESS, _("Success")),
    (ACTIVITY_LOG_LEVEL_WARNING, _("Warning")),
    (ACTIVITY_LOG_LEVEL_ERROR, _("Error")),
)

# For activity log type choices
ACTIVITY_LOG_TYPE_NOTIFICATION = "notification"
ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED = "payment_succeeded"
ACTIVITY_LOG_TYPE_PAYMENT_FAILED = "payment_failed"
ACTIVITY_LOG_TYPE_PAYMENT_REFUNDED = "payment_refunded"

ACTIVITY_LOG_TYPE_CHOICES = (
    (ACTIVITY_LOG_TYPE_NOTIFICATION, _("Notification")),
    (ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED, _("Payment succeeded")),
    (ACTIVITY_LOG_TYPE_PAYMENT_FAILED, _("Payment failed")),
    (ACTIVITY_LOG_TYPE_PAYMENT_REFUNDED, _("Payment refunded")),
)

PAYMENT_STATE_PENDING = "pending"
PAYMENT_STATE_PAID = "paid"
PAYMENT_STATE_REFUSED = "refused"
PAYMENT_STATE_REFUNDED = "refunded"
PAYMENT_STATE_CANCELED = "canceled"

PAYMENT_STATE_CHOICES = (
    (PAYMENT_STATE_PENDING, _("Pending")),
    (PAYMENT_STATE_PAID, _("Paid")),
    (PAYMENT_STATE_REFUSED, _("Refused")),
    (PAYMENT_STATE_REFUNDED, _("Refunded")),
    (PAYMENT_STATE_CANCELED, _("Canceled")),
)
