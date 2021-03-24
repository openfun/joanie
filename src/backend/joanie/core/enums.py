"""
Core application enums declaration
"""
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

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

ORDER_STATE_PENDING = "pending"  # waiting for payment and enrollment
ORDER_STATE_CANCELED = "canceled"
ORDER_STATE_FAILED = "failed"
ORDER_STATE_IN_PROGRESS = "in_progress"
ORDER_STATE_FINISHED = "finished"

ORDER_STATE_CHOICES = (
    (ORDER_STATE_PENDING, _("Pending")),  # default
    (ORDER_STATE_CANCELED, pgettext_lazy("As in: the order is cancelled.", "Canceled")),
    (ORDER_STATE_FAILED, pgettext_lazy("As in: the order is failed.", "Failed")),
    (ORDER_STATE_IN_PROGRESS, _("In progress")),
    (ORDER_STATE_FINISHED, pgettext_lazy("As in: the order is finished.", "Finished")),
)

ENROLLMENT_STATE_PENDING = "pending"
ENROLLMENT_STATE_IN_PROGRESS = "in_progress"
ENROLLMENT_STATE_VALIDATED = "validated"
ENROLLMENT_STATE_CANCELED = "canceled"
ENROLLMENT_STATE_FAILED = "failed"

ENROLLMENT_STATE_CHOICES = (
    (ENROLLMENT_STATE_PENDING, _("Pending")),  # default
    (ENROLLMENT_STATE_IN_PROGRESS, _("In progress")),
    (
        ENROLLMENT_STATE_VALIDATED,
        pgettext_lazy("As in: the enrollment is validated.", "Validated"),
    ),
    (
        ENROLLMENT_STATE_CANCELED,
        pgettext_lazy("As in: the enrollment is cancelled.", "Canceled"),
    ),
    (
        ENROLLMENT_STATE_FAILED,
        pgettext_lazy("As in: the enrollment is failed.", "Failed"),
    ),
)
