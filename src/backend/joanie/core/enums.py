
from django.utils.translation import gettext_lazy as _


PRODUCT_TYPE_CREDENTIAL = 'credential'
PRODUCT_TYPE_ENROLLMENT = 'enrollment'
PRODUCT_TYPE_CERTIFICATE = 'certificate'

PRODUCT_TYPE_CHOICES = (
    (PRODUCT_TYPE_CREDENTIAL, _("Credential")),
    (PRODUCT_TYPE_ENROLLMENT, _("Enrollment")),
    (PRODUCT_TYPE_CERTIFICATE, _("Certificate")),
)


ORDER_STATE_PENDING = 'pending'  # waiting for payment and enrollment
ORDER_STATE_CANCELED = 'canceled'
ORDER_STATE_FAILURE = 'failure'
ORDER_STATE_IN_PROGRESS = 'in_progress'
ORDER_STATE_FINISHED = 'finished'

ORDER_STATE_CHOICES = (
    (ORDER_STATE_PENDING, _("Pending")),  # default
    (ORDER_STATE_CANCELED, _("Canceled")),
    (ORDER_STATE_FAILURE, _("Failure")),
    (ORDER_STATE_IN_PROGRESS, _("In progress")),
    (ORDER_STATE_FINISHED, _("Finished")),
)

ENROLLMENT_STATE_PENDING = 'pending'  # default
ENROLLMENT_STATE_IN_PROGRESS = 'in_progress'
ENROLLMENT_STATE_VALIDATED = 'validated'
ENROLLMENT_STATE_CANCELED = 'canceled'
ENROLLMENT_STATE_FAILED = 'failed'

ENROLLMENT_STATE_CHOICES = (
    (ENROLLMENT_STATE_PENDING, _("Pending")),
    (ENROLLMENT_STATE_IN_PROGRESS, _("In progress")),
    (ENROLLMENT_STATE_VALIDATED, _("Validated")),
    (ENROLLMENT_STATE_CANCELED, _("Canceled")),
    (ENROLLMENT_STATE_FAILED, _("Failed")),
)
