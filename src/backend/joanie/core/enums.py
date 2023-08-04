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
ORDER_STATE_SUBMITTED = "submitted"  # order information have been validated
ORDER_STATE_PENDING = "pending"  # payment has failed but can be retried
ORDER_STATE_CANCELED = "canceled"  # has been canceled
ORDER_STATE_VALIDATED = "validated"  # is free or has an invoice linked

ORDER_STATE_CHOICES = (
    (ORDER_STATE_DRAFT, _("Draft")),  # default
    (ORDER_STATE_SUBMITTED, _("Submitted")),
    (ORDER_STATE_PENDING, _("Pending")),
    (ORDER_STATE_CANCELED, pgettext_lazy("As in: the order is cancelled.", "Canceled")),
    (
        ORDER_STATE_VALIDATED,
        pgettext_lazy("As in: the order is validated.", "Validated"),
    ),
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
