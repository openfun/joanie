"""
Declare and configure the models for the courses part
"""

import itertools
import logging
from collections.abc import Mapping
from datetime import MAXYEAR, datetime
from datetime import timezone as tz
from typing import TypedDict

from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField
from easy_thumbnails.fields import ThumbnailerImageField
from parler import models as parler_models
from rest_framework.reverse import reverse
from url_normalize import url_normalize

from joanie.core import enums, exceptions, utils
from joanie.core.fields.multiselect import MultiSelectField
from joanie.core.models.accounts import User
from joanie.core.models.base import BaseModel
from joanie.core.models.contracts import Contract
from joanie.core.utils import normalize_phone_number, payment_schedule, webhooks
from joanie.core.utils.course_run.aggregate_course_runs_dates import (
    aggregate_course_runs_dates,
)
from joanie.core.utils.discount import calculate_price
from joanie.lms_handler import LMSHandler
from joanie.signature.backends import get_signature_backend

# pylint: disable=too-many-lines

MAX_DATE = datetime(MAXYEAR, 12, 31, tzinfo=tz.utc)

logger = logging.getLogger(__name__)


class CourseStateType(TypedDict):
    """Type of course state."""

    priority: int
    datetime: datetime | None
    call_to_action: str | None
    text: str


class CourseState(Mapping):
    """An immutable object to describe a course (resp. course run) state."""

    _d: CourseStateType

    (
        ONGOING_OPEN,
        FUTURE_OPEN,
        ARCHIVED_OPEN,
        FUTURE_NOT_YET_OPEN,
        FUTURE_CLOSED,
        ONGOING_CLOSED,
        ARCHIVED_CLOSED,
        TO_BE_SCHEDULED,
    ) = range(8)

    STATE_CALLS_TO_ACTION = {
        ONGOING_OPEN: _("enroll now"),
        FUTURE_OPEN: _("enroll now"),
        ARCHIVED_OPEN: _("study now"),
        FUTURE_NOT_YET_OPEN: None,
        FUTURE_CLOSED: None,
        ONGOING_CLOSED: None,
        ARCHIVED_CLOSED: None,
        TO_BE_SCHEDULED: None,
    }

    STATE_TEXTS = {
        ONGOING_OPEN: _("closing on"),
        FUTURE_OPEN: _("starting on"),
        ARCHIVED_OPEN: _("closing on"),
        FUTURE_NOT_YET_OPEN: _("starting on"),
        FUTURE_CLOSED: _("enrollment closed"),
        ONGOING_CLOSED: _("on-going"),
        ARCHIVED_CLOSED: _("archived"),
        TO_BE_SCHEDULED: _("to be scheduled"),
    }

    def __init__(self, priority, date_time=None):
        """
        Initialize a course state with a priority and optionally a datetime.

        Several states are possible for a course run each of which is given a priority. The
        lower the priority, the more interesting the course run is (a course run open for
        enrollment is more interesting than an archived course run):
        - 0 | ONGOING_OPEN: a run is ongoing and open for enrollment
              > "closing on": {enrollment_end}
        - 1 | FUTURE_OPEN: a run is future and open for enrollment > "starting on": {start}
        - 2 | ARCHIVED_OPEN: a run is past but open for enrollment > "closing on": {enrollment_end}
        - 3 | FUTURE_NOT_YET_OPEN: a run is future and not yet open for enrollment
              > "starting on": {start}
        - 4 | FUTURE_CLOSED: a run is future and no more open for enrollment > "closed": {None}
        - 5 | ONGOING_CLOSED: a run is ongoing but closed for enrollment > "on going": {None}
        - 6 | ARCHIVED_CLOSED: there's a finished run in the past > "archived": {None}
        - 7 | TO_BE_SCHEDULED: there is no run with a start date or no run at all
              > "to be scheduled": {None}
        """
        # Check that `date_time` is set when it should be
        if date_time is None and priority in [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
            CourseState.FUTURE_NOT_YET_OPEN,
        ]:
            raise ValidationError(
                f"date_time should not be null for a {priority:d} course state."
            )

        # A special case of being open is when enrollment never ends
        text = self.STATE_TEXTS[priority]
        if (
            priority in [CourseState.ONGOING_OPEN, CourseState.ARCHIVED_OPEN]
            and date_time.year == MAXYEAR
        ):
            text = _("forever open")
            date_time = None
        kwargs = {
            "priority": priority,
            "datetime": date_time,
            "call_to_action": self.STATE_CALLS_TO_ACTION[priority],
            "text": text,
        }
        self._d = {**kwargs}

    def __str__(self):
        """String representation"""
        return str(self._d["text"])

    def __iter__(self):
        """Iterate on the inner dictionary."""
        return iter(self._d)

    def __len__(self):
        """Return length of the inner dictionary."""
        return len(self._d)

    def __getitem__(self, key):
        """Access the inner dictionary."""
        return self._d[key]

    def __lt__(self, other):
        """Make it easy to compare two course states."""
        return self._d["priority"] < other["priority"]


class Organization(parler_models.TranslatableModel, BaseModel):
    """
    Organization model represents and records entities that manage courses.
    It could be a university or a training company for example.
    It's required to create course page in cms.
    It will allow to validate user enrollment to course or not, depending on various criteria.
    """

    code = models.CharField(_("code"), unique=True, db_index=True, max_length=100)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    representative = models.CharField(
        _("representative"),
        help_text=_("representative fullname (to sign certificate for example)"),
        max_length=100,
        blank=True,
    )
    signature = models.ImageField(_("signature"), blank=True)
    logo = ThumbnailerImageField(_("logo"), blank=True)
    country = CountryField(
        _("country"),
        help_text=_(
            "Country field will be deprecated soon in order to be replaced by address relation."
        ),
        default=settings.JOANIE_DEFAULT_COUNTRY_CODE,
    )
    enterprise_code = models.CharField(
        verbose_name=_("Enterprise code"),  # e.g : SIRET in France
        max_length=50,
        blank=True,
        null=True,
    )
    activity_category_code = models.CharField(
        verbose_name=_("Activity category code"),  # e.g : APE in France
        max_length=50,
        blank=True,
    )
    representative_profession = models.CharField(
        verbose_name=_("Profession of the organization's representative"),
        help_text=_("representative profession"),
        max_length=100,
        blank=True,
        null=True,
    )
    signatory_representative = models.CharField(
        verbose_name=_("Signatory representative"),
        help_text=_(
            "This field is optional. If it is set, you must set the field"
            "'signatory_representative_profession' as well"
        ),
        max_length=100,
        blank=True,
        null=True,
    )
    signatory_representative_profession = models.CharField(
        verbose_name=_("Profession of the signatory representative"),
        help_text=_("signatory representative profession"),
        max_length=100,
        blank=True,
        null=True,
    )
    contact_phone = models.CharField(
        verbose_name=_("Contact phone number"),
        max_length=40,
        blank=True,
    )
    contact_email = models.CharField(
        verbose_name=_("Contact email"), max_length=100, blank=True
    )
    dpo_email = models.CharField(
        verbose_name=_("Data protection officer email"),
        max_length=100,
        blank=True,
    )

    @property
    def offerings(self):
        """
        Return the course product relation associated with the organization.
        """
        return self.offerings

    @offerings.setter
    def set_offerings(self, value):
        """
        Set the course product relation associated with the organization.
        """
        self.offerings = value

    class Meta:
        db_table = "joanie_organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["-created_on"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        signatory_representative__isnull=False,
                        signatory_representative_profession__isnull=False,
                    )
                    | models.Q(
                        signatory_representative__isnull=True,
                        signatory_representative_profession__isnull=True,
                    )
                ),
                name="both_signatory_representative_fields_must_be_set",
                violation_error_message=_(
                    "Both signatory representative fields must be set."
                ),
            )
        ]

    def __str__(self):
        return (
            f"[{self.code}] {self.safe_translation_getter('title', any_language=True)}"
        )

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness. We also normalize the
        `contact_phone` value for consistency in database.
        """
        if phone_number := self.contact_phone:
            self.contact_phone = normalize_phone_number(phone_number)
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self.accesses.filter(user=user).values("role")[0]["role"]
                except (OrganizationAccess.DoesNotExist, IndexError):
                    role = None

            is_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        return {
            "get": True,
            "patch": is_owner_or_admin,
            "put": is_owner_or_admin,
            "delete": role == enums.OWNER,
            "manage_accesses": is_owner_or_admin,
            "sign_contracts": role == enums.OWNER,
        }

    def signature_backend_references_to_sign(self, **kwargs):
        """
        Return the list of references that should be signed by the organization.
        """
        filters = Q()
        if contract_ids := kwargs.get("contract_ids"):
            filters &= Q(id__in=contract_ids)
        if relation_ids := kwargs.get("offering_ids"):
            filters &= Q(order__product__offerings__id__in=relation_ids)

        contracts_to_sign = list(
            Contract.objects.filter(
                filters,
                signature_backend_reference__isnull=False,
                submitted_for_signature_on__isnull=False,
                student_signed_on__isnull=False,
                order__organization=self,
            )
            .exclude(order__state=enums.ORDER_STATE_CANCELED)
            .values_list("id", "signature_backend_reference")
        )

        if contract_ids and len(contracts_to_sign) != len(contract_ids):
            raise exceptions.NoContractToSignError(
                "Some contracts are not available for this organization."
            )

        return tuple(zip(*contracts_to_sign, strict=True)) or ((), ())

    def contracts_signature_link(self, user: User, **kwargs):
        """
        Retrieve a signature invitation link for all available contracts.
        """
        ids, references = self.signature_backend_references_to_sign(**kwargs)
        if not references:
            raise exceptions.NoContractToSignError(
                "No contract to sign for this organization."
            )
        backend_signature = get_signature_backend()
        return (
            backend_signature.get_signature_invitation_link(user.email, references),
            ids,
        )


class OrganizationAccess(BaseModel):
    """Link table between organizations and users"""

    ROLE_CHOICES = (
        (enums.OWNER, _("owner")),
        (enums.ADMIN, _("administrator")),
        (enums.MEMBER, _("member")),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organization_accesses"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=enums.MEMBER)

    class Meta:
        db_table = "joanie_organization_access"
        verbose_name = _("Organization access")
        verbose_name_plural = _("Organization accesses")
        unique_together = ("organization", "user")
        ordering = ["-created_on"]

    def __str__(self):
        role = capfirst(self.get_role_display())
        return (
            f"{role:s} role for {self.user.username:s} on {self.organization.title:s}"
        )

    def save(self, *args, **kwargs):
        """Make sure we keep at least one owner for the organization."""
        self.full_clean()

        if self.pk and self.role != enums.OWNER:
            accesses = self._meta.model.objects.filter(
                organization=self.organization, role=enums.OWNER
            ).only("pk")
            if len(accesses) == 1 and accesses[0].pk == self.pk:
                raise PermissionDenied(
                    "An organization should keep at least one owner."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disallow deleting the last owner."""
        if (
            self.role == enums.OWNER
            and self._meta.model.objects.filter(
                organization=self.organization, role=enums.OWNER
            ).count()
            == 1
        ):
            raise PermissionDenied("An organization should keep at least one owner.")
        return super().delete(*args, **kwargs)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_organization_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self._meta.model.objects.filter(
                        organization=self.organization_id, user=user
                    ).values("role")[0]["role"]
                except (OrganizationAccess.DoesNotExist, IndexError):
                    role = None

            is_organization_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        if self.role == enums.OWNER:
            can_delete = (
                user.id == self.user_id
                and self.organization.accesses.filter(role=enums.OWNER).count() > 1
            )
            set_role_to = [enums.ADMIN, enums.MEMBER] if can_delete else []
        else:
            can_delete = is_organization_owner_or_admin
            set_role_to = []
            if role == enums.OWNER:
                set_role_to.append(enums.OWNER)
            if is_organization_owner_or_admin:
                set_role_to.extend([enums.ADMIN, enums.MEMBER])

        # Remove the current role as we don't want to propose it as an option
        try:
            set_role_to.remove(self.role)
        except ValueError:
            pass

        return {
            "delete": can_delete,
            "get": bool(role),
            "patch": bool(set_role_to),
            "put": bool(set_role_to),
            "set_role_to": set_role_to,
        }


class Course(parler_models.TranslatableModel, BaseModel):
    """
    Course model represents and records a course in the cms catalog.
    A new course created will initialize a cms page.
    """

    code = models.CharField(_("code"), max_length=100, unique=True, db_index=True)
    cover = ThumbnailerImageField(_("cover"), blank=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    organizations = models.ManyToManyField(
        to=Organization,
        related_name="courses",
        verbose_name=_("organizations"),
    )
    products = models.ManyToManyField(
        "Product",
        related_name="courses",
        through="CourseProductRelation",
        through_fields=("course", "product"),
        verbose_name=_("products"),
        blank=True,
    )
    # to represent the volume in seconds to accomplish the course theoretically
    effort = models.DurationField(
        verbose_name="Effort in seconds",
        blank=True,
        null=True,
        help_text="The duration effort required in seconds",
    )

    @property
    def offerings(self):
        """
        Return the course product relation associated with the course.
        """
        return self.offerings

    @offerings.setter
    def set_offerings(self, value):
        """
        Set the course product relation associated with the course.
        """
        self.offerings = value

    class Meta:
        db_table = "joanie_course"
        ordering = ("code",)
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)

    @property
    def state(self) -> str:
        """
        The state of the course carrying information on what to display on a course glimpse.

        The game is to find the highest priority state for this course among
        its course runs and its products.
        """
        # The default state is for a course that has no course runs or products
        best_state = CourseState(CourseState.TO_BE_SCHEDULED)
        course_runs = self.course_runs.all()
        products = self.products.all()

        for instance in itertools.chain(course_runs, products):
            state = instance.state
            best_state = min(state, best_state)
            if state["priority"] == CourseState.ONGOING_OPEN:
                # We found the best state, don't waste more time
                break

        return best_state

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness
        """
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_equivalent_course_run_dates(self, ignore_archived=False):
        """
        Return a dict of dates equivalent to course run dates
        by aggregating dates of all target course runs as follows:
        - start: Pick the earliest start date
        - end: Pick the latest end date
        - enrollment_start: Pick the latest enrollment start date
        - enrollment_end: Pick the earliest enrollment end date
        """
        return aggregate_course_runs_dates(
            self.course_runs,
            ignore_archived=ignore_archived,
        )

    def get_selling_organizations(self, product=None):
        """
        Return the list of organizations selling a product for the course.
        If no product is provided, return the list of organizations selling
        any product for the course.
        """

        if product is None:
            qs = self.offerings.all()
        else:
            qs = self.offerings.filter(product=product)

        return Organization.objects.filter(
            id__in=qs.distinct()
            .only("organizations")
            .values_list("organizations", flat=True)
        )

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self.accesses.filter(user=user).values("role")[0]["role"]
                except (CourseAccess.DoesNotExist, IndexError):
                    role = None

            is_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        return {
            "get": True,
            "patch": is_owner_or_admin,
            "put": is_owner_or_admin,
            "delete": role == enums.OWNER,
            "manage_accesses": is_owner_or_admin,
        }


class CourseAccess(BaseModel):
    """Link table between courses and users"""

    ROLE_CHOICES = (
        (enums.OWNER, _("owner")),
        (enums.ADMIN, _("administrator")),
        (enums.INSTRUCTOR, _("instructor")),
        (enums.MANAGER, _("manager")),
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_accesses"
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=enums.INSTRUCTOR
    )

    class Meta:
        db_table = "joanie_course_access"
        verbose_name = _("Course access")
        verbose_name_plural = _("Course accesses")
        unique_together = ("course", "user")
        ordering = ["-created_on"]

    def __str__(self):
        role = capfirst(self.get_role_display())
        return f"{role:s} role for {self.user.username:s} on {self.course.title:s}"

    def save(self, *args, **kwargs):
        """Make sure we keep at least one owner for the course."""
        self.full_clean()

        if self.pk and self.role != enums.OWNER:
            accesses = self._meta.model.objects.filter(
                course=self.course, role=enums.OWNER
            ).only("pk")
            if len(accesses) == 1 and accesses[0].pk == self.pk:
                raise PermissionDenied("A course should keep at least one owner.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disallow deleting the last owner."""
        if (
            self.role == enums.OWNER
            and self._meta.model.objects.filter(
                course=self.course, role=enums.OWNER
            ).count()
            == 1
        ):
            raise PermissionDenied("A course should keep at least one owner.")
        return super().delete(*args, **kwargs)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_course_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self._meta.model.objects.filter(
                        course=self.course_id, user=user
                    ).values("role")[0]["role"]
                except (CourseAccess.DoesNotExist, IndexError):
                    role = None

            is_course_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        if self.role == enums.OWNER:
            can_delete = (
                user.id == self.user_id
                and self.course.accesses.filter(role=enums.OWNER).count() > 1
            )
            set_role_to = (
                [enums.ADMIN, enums.INSTRUCTOR, enums.MANAGER] if can_delete else []
            )
        else:
            can_delete = is_course_owner_or_admin
            set_role_to = []
            if role == enums.OWNER:
                set_role_to.append(enums.OWNER)
            if is_course_owner_or_admin:
                set_role_to.extend([enums.ADMIN, enums.INSTRUCTOR, enums.MANAGER])

        # Remove the current role as we don't want to propose it as an option
        try:
            set_role_to.remove(self.role)
        except ValueError:
            pass

        return {
            "delete": can_delete,
            "get": bool(role),
            "patch": bool(set_role_to),
            "put": bool(set_role_to),
            "set_role_to": set_role_to,
        }


class CourseProductRelation(BaseModel):
    """
    CourseProductRelation model allows defining the products sold on a given course.

    It is used as through model in a ManyToMany relation between a Course and a Product.

    The `organizations` field defines what organizations are selling the product on the
    course. If several organizations are selling a product on a course, the buyer is asked
    to choose from which organization they want to buy it.
    """

    course = models.ForeignKey(
        to=Course,
        verbose_name=_("course"),
        related_name="offerings",
        on_delete=models.RESTRICT,
    )
    product = models.ForeignKey(
        to="Product",
        verbose_name=_("product"),
        related_name="offerings",
        on_delete=models.CASCADE,
    )
    organizations = models.ManyToManyField(
        to=Organization,
        related_name="offerings",
        verbose_name=_("organizations"),
    )

    class Meta:
        db_table = "joanie_course_product_relation"
        unique_together = ("product", "course")
        verbose_name = _("Course relation to a product")
        verbose_name_plural = _("Courses relations to products")
        ordering = ["-created_on"]

    def __str__(self):
        return f"{self.course}: {self.product}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Delete the relation if it can be edited, raise a ValidationError otherwise."""
        if not self.can_edit:
            raise ValidationError(_("You cannot delete this offering."))
        return super().delete(using=using, keep_parents=keep_parents)

    @property
    def uri(self):
        """
        Build the api url to get the detail of the provided course product relation.
        """
        site = Site.objects.get_current()
        resource_path = reverse(
            "offerings-detail",
            kwargs={
                "course_id": self.course.code,  # pylint: disable=no-member
                "pk_or_product_id": self.product_id,  # pylint: disable=no-member
            },
        )

        return f"https://{site.domain}{resource_path}"

    @property
    def can_edit(self):
        """Return True if the relation can be edited, False otherwise."""
        Order = apps.get_model("core", "Order")  # pylint: disable=invalid-name
        return not Order.objects.filter(
            product=self.product, course=self.course
        ).exists()

    @property
    def is_withdrawable(self):
        """
        Return True if the product has a withdrawal period.

        Read the docstring of core.utils.payment_schedule.has_withdrawal_period method
        for further information.
        """
        if self.product.type != enums.PRODUCT_TYPE_CERTIFICATE:  # pylint: disable=no-member
            instance = self.product
        else:
            instance = self.course

        start_date = instance.get_equivalent_course_run_dates(ignore_archived=True)[  # pylint: disable=no-member
            "start"
        ]

        if start_date is None:
            return True

        return payment_schedule.has_withdrawal_period(
            timezone.localdate(), start_date.date()
        )

    @property
    def rules(self):
        """
        Compute the current offering rules for the course product relation.
        """
        offering_rule_found = None
        offering_rule_is_blocking = False
        for offering_rule in self.offering_rules.all():
            if offering_rule.is_enabled:
                offering_rule_is_blocking = (
                    not offering_rule.is_assignable and not offering_rule.discount
                )
                offering_rule_found = offering_rule

        discounted_price = None
        discount_amount = None
        discount_rate = None
        discount = None
        description = None
        discount_start = None
        discount_end = None
        nb_available_seats = None
        has_seat_limit = False
        has_seats_left = True

        if offering_rule := offering_rule_found:
            description = getattr(offering_rule, "description", None)
            discount_start = offering_rule.start
            discount_end = offering_rule.end
            if not offering_rule.discount or offering_rule.available_seats:
                nb_available_seats = offering_rule.available_seats
                has_seat_limit = (
                    offering_rule.nb_seats is not None
                    and nb_available_seats is not None
                )
                has_seats_left = not has_seat_limit or (
                    has_seat_limit and nb_available_seats > 0
                )
            if offering_rule.discount and offering_rule.is_assignable:
                discounted_price = calculate_price(
                    self.product.price,  # pylint: disable=no-member
                    offering_rule.discount,
                )
                discount_amount = offering_rule.discount.amount
                discount_rate = offering_rule.discount.rate
                discount = str(offering_rule.discount)

        return {
            "discounted_price": discounted_price,
            "discount_amount": discount_amount,
            "discount_rate": discount_rate,
            "discount": discount,
            "description": description,
            "discount_start": discount_start,
            "discount_end": discount_end,
            "nb_available_seats": nb_available_seats,
            "has_seat_limit": has_seat_limit,
            "has_seats_left": has_seats_left or not offering_rule_is_blocking,
        }


class CourseRun(parler_models.TranslatableModel, BaseModel):
    """
    Course run represents and records the occurrence of a course between a start
    and an end date.
    """

    course = models.ForeignKey(
        to=Course,
        on_delete=models.PROTECT,
        related_name="course_runs",
        verbose_name=_("course"),
    )

    # link to lms resource
    resource_link = models.CharField(_("resource link"), max_length=200, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    # availability period
    start = models.DateTimeField(_("course start"), blank=True, null=True)
    end = models.DateTimeField(_("course end"), blank=True, null=True)
    # enrollment allowed period
    enrollment_start = models.DateTimeField(_("enrollment date"), blank=True, null=True)
    enrollment_end = models.DateTimeField(_("enrollment end"), blank=True, null=True)
    languages = MultiSelectField(
        max_choices=50,
        max_length=255,  # MySQL does not allow max_length > 255
        # Language choices are made lazy so that we can override them in our tests.
        # When set directly, they are evaluated too early and can't be changed with the
        # "override_settings" utility.
        choices=lazy(lambda: enums.ALL_LANGUAGES, tuple)(),
        help_text=_("The list of languages in which the course content is available."),
    )
    is_gradable = models.BooleanField(_("is gradable"), default=False)
    is_listed = models.BooleanField(
        _("is listed"),
        default=False,
        help_text=_(
            "If checked the course run will be included in the list of course runs "
            "available for enrollment on the related course page."
        ),
    )

    class Meta:
        db_table = "joanie_course_run"
        verbose_name = _("Course run")
        verbose_name_plural = _("Course runs")
        ordering = ["-created_on"]

    def __str__(self):
        return (
            f"{self.safe_translation_getter('title', any_language=True)} "
            f"[{self.state.get('text')}]"
        )

    @property
    def uri(self):
        """Return the uri of Course Run."""
        site = Site.objects.get_current()
        resource_path = reverse("course-runs-detail", kwargs={"id": self.id})

        return f"https://{site.domain:s}{resource_path:s}"

    def get_serialized(self, visibility=None, certifying=True, product=None):
        """
        Return data for the course run that will be sent to the remote web hooks.
        Course run visibility can be forced via the eponym argument.
        """

        if (
            visibility is not None
            and visibility not in enums.CATALOG_VISIBILITY_CHOICES
        ):
            raise ValueError(
                f"Invalid visibility: {visibility}. Must be one "
                f"of {enums.CATALOG_VISIBILITY_CHOICES} or None"
            )

        certificate_discounted_price = None
        certificate_discount = None
        if certifying and product:
            offering = (
                CourseProductRelation.objects.get(course=self.course, product=product)
                if product
                else None
            )

            if offering and offering.rules.get("discounted_price"):
                certificate_discounted_price = offering.rules["discounted_price"]
                certificate_discount = offering.rules.get("discount")

        return {
            "catalog_visibility": visibility
            or (enums.COURSE_AND_SEARCH if self.is_listed else enums.HIDDEN),
            "course": self.course.code,
            "end": self.end.isoformat() if self.end else None,
            "enrollment_start": self.enrollment_start.isoformat()
            if self.enrollment_start
            else None,
            "enrollment_end": self.enrollment_end.isoformat()
            if self.enrollment_end
            else None,
            "certificate_offer": self.get_certificate_offer() if certifying else None,
            "certificate_price": product.price if (certifying and product) else None,
            "certificate_discounted_price": certificate_discounted_price,
            "certificate_discount": certificate_discount,
            "languages": self.languages,
            "resource_link": self.uri,
            "start": self.start.isoformat() if self.start else None,
        }

    def get_certificate_offer(self):
        """
        Return certificate offer if the related course has a certificate product.
        According to the product price, the offer is set to 'paid' or 'free'.
        """
        max_product_price = self.course.products.filter(
            type=enums.PRODUCT_TYPE_CERTIFICATE
        ).aggregate(models.Max("price"))["price__max"]

        if max_product_price is None:
            return None

        return (
            enums.COURSE_OFFER_PAID
            if max_product_price > 0
            else enums.COURSE_OFFER_FREE
        )

    # pylint: disable=invalid-name
    def get_equivalent_serialized_course_runs_for_related_products(
        self, visibility=None
    ):
        """
        Returns the equivalent serialized course runs for the products related to the
        current course run.
        """
        products = self.course.products.model.objects.filter(
            models.Q(target_course_relations__course_runs__isnull=True)
            | models.Q(target_course_relations__course_runs=self),
            target_course_relations__course=self.course,
        )

        return self.course.products.model.get_equivalent_serialized_course_runs_for_products(
            products, visibility=visibility
        )

    # pylint: disable=too-many-return-statements
    # ruff: noqa: PLR0911
    @staticmethod
    def compute_state(start=None, end=None, enrollment_start=None, enrollment_end=None):
        """
        Compute at the current time the state of a course run that would have the dates
        passed in argument.

        A static method not using the instance allows to call it with an Elasticsearch result.
        """
        if not start or not enrollment_start:
            return CourseState(CourseState.TO_BE_SCHEDULED)

        # course run end dates are not required and should default to forever
        # e.g. a course run with no end date is presumed to be always on-going
        end = end or MAX_DATE
        enrollment_end = enrollment_end or MAX_DATE

        now = timezone.now()
        if start < now:
            if end > now:
                if enrollment_start <= now < enrollment_end:
                    # ongoing open
                    return CourseState(CourseState.ONGOING_OPEN, enrollment_end)
                # ongoing closed
                return CourseState(CourseState.ONGOING_CLOSED)
            if enrollment_start < now < enrollment_end:
                # archived open
                return CourseState(CourseState.ARCHIVED_OPEN, enrollment_end)
            # archived closed
            return CourseState(CourseState.ARCHIVED_CLOSED)
        if enrollment_start > now:
            # future not yet open
            return CourseState(CourseState.FUTURE_NOT_YET_OPEN, start)
        if enrollment_end > now:
            # future open
            return CourseState(CourseState.FUTURE_OPEN, start)
        # future already closed
        return CourseState(CourseState.FUTURE_CLOSED)

    @property
    def state(self) -> CourseStateType:
        """Return the state of the course run at the current time."""
        return self.compute_state(
            self.start, self.end, self.enrollment_start, self.enrollment_end
        )

    def clean(self):
        """
        Normalize the resource_link url and prevent data integrity error when course is
        updated.
        """
        self.resource_link = url_normalize(self.resource_link)

        # If the course run is updating and the course field has changed ...
        if self.created_on:
            old_course_id = (
                CourseRun.objects.only("course_id").get(pk=self.pk).course_id
            )
            if old_course_id != self.course_id:
                # ... Check the course run instance does not rely on product/order relations
                if (
                    self.product_relations.count() > 0
                    or self.order_relations.count() > 0
                ):
                    raise ValidationError(
                        _(
                            "This course run relies on a product relation. "
                            "So you cannot modify its course."
                        )
                    )

        super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None):
        """
        We need to synchronize with webhooks upon deletion. We could have used the signal but it
        also triggers on query deletes and is being called as many times as there are objects in
        the query. This would generate many separate calls to the webhook and would not scale. We
        decided to not provide synchronization for the moment on bulk deletes and leave it up to
        the developer to handle these cases correctly.
        """
        # Course run will be deleted, we synchronize it setting its visibility to hidden
        serialized_course_runs = [self.get_serialized(visibility=enums.HIDDEN)]

        super().delete(using=using)

        # Now synchronize the related products by recomputing the equivalent serialized course run
        serialized_course_runs.extend(
            self.get_equivalent_serialized_course_runs_for_related_products()
        )
        webhooks.synchronize_course_runs(serialized_course_runs)

    def can_enroll(self, user):
        """
        Verify if a user can enroll in a course run that is open, when the user does not yet
        have any active enrollment for that course in another opened course run.
        """
        now = timezone.now()
        user_enrollment_ids = user.enrollments.values_list("id", flat=True)

        return not (
            user.enrollments.filter(id__in=user_enrollment_ids, is_active=True).exists()
            and user.enrollments.filter(
                is_active=True, course_run__course=self.course, course_run__end__gte=now
            ).exists()
        )


class Enrollment(BaseModel):
    """
    Enrollment model represents and records lms enrollment state for course run
    as part of an order
    """

    course_run = models.ForeignKey(
        to=CourseRun,
        verbose_name=_("course run"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    user = models.ForeignKey(
        to=User,
        verbose_name=_("user"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    is_active = models.BooleanField(
        help_text=_("Ticked if the user is enrolled to the course run."),
        verbose_name="is active",
    )
    state = models.CharField(
        _("state"), choices=enums.ENROLLMENT_STATE_CHOICES, max_length=50, blank=True
    )
    was_created_by_order = models.BooleanField(
        help_text=_(
            "Ticked if the enrollment has been initially created in the scope of an order."
        ),
        verbose_name=_("was created by order"),
        default=False,
    )

    class Meta:
        db_table = "joanie_enrollment"
        unique_together = ("course_run", "user")
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")
        ordering = ["-created_on"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_is_active = self.is_active

    def __str__(self):
        active = _("active") if self.is_active else _("inactive")
        return f"[{active}][{self.state}] {self.user} for {self.course_run}"

    @property
    def grade_cache_key(self):
        """The cache key used to store enrollment's grade."""
        return f"grade_{self.id}"

    @property
    def is_passed(self):
        """Get enrollment grade then return the `passed` property value or False"""
        grade = self.get_grade()

        return grade["passed"] if grade else False

    def get_grade(self):
        """Retrieve the grade from the related LMS then store result in cache."""
        grade = cache.get(self.grade_cache_key)

        if grade is None:
            lms = LMSHandler.select_lms(self.course_run.resource_link)

            if lms is None:
                logger.error(
                    "Course run %s has no related lms.",
                    self.course_run.id,
                )
            else:
                try:
                    grade = lms.get_grades(
                        username=self.user.username,
                        resource_link=self.course_run.resource_link,
                    )
                except exceptions.GradeError:
                    pass
                else:
                    cache.set(
                        self.grade_cache_key,
                        grade,
                        settings.JOANIE_ENROLLMENT_GRADE_CACHE_TTL,
                    )

        return grade

    def clean(self):
        """
        Clean instance fields and raise a ValidationError in case of issue.

        Sometimes a course run can be available for free enrollment
        (course_run.is_listed = True) and also included in a product. So a user can
        enroll to this course run for free or in the scope of an order. The flag
        `was_created_by_order` aims to store the context of the enrollment creation. If
        the enrollment is created in the scope of an order, this flag must be set to
        True. Otherwise, in the case of a free enrollment, the flag must be set to
        False.

        --> *1
        But if the related course run is not listed (so not available for free
        enrollment) the flag `was_created_by_order` cannot be set to False.

        --> *2
        And if the related course run is not linked to any product, the flag
        `was_created_by_order` cannot be set to True.
        """
        # Forbid creating a free enrollment if the related course run is not listed and
        # if the course relies on a product and the owner doesn't purchase it.
        if self.is_active and not self.course_run.is_listed:
            if self.was_created_by_order is False:
                # --> *1
                message = _(
                    "You cannot enroll to a non-listed course run out of the scope of an order."
                )
                raise ValidationError({"was_created_by_order": [message]})
            if self.course_run.course.targeted_by_products.exists():
                validated_user_orders = self.user.orders.filter(
                    (
                        models.Q(
                            offerings__course_runs__isnull=True,
                            target_courses__course_runs=self.course_run,
                        )
                        | models.Q(offerings__course_runs=self.course_run)
                    ),
                    (
                        models.Q(
                            product__contract_definition__isnull=False,
                            contract__student_signed_on__isnull=False,
                        )
                        | models.Q(
                            product__contract_definition__isnull=True,
                        )
                    ),
                    state__in=enums.ORDER_STATE_ALLOW_ENROLLMENT,
                )
                if validated_user_orders.count() == 0:
                    message = _(
                        f'Course run "{self.course_run.id!s}" '
                        "requires a valid order to enroll."
                    )
                    raise ValidationError({"__all__": [message]})
            else:
                message = _("You are not allowed to enroll to a course run not listed.")
                raise ValidationError({"__all__": [message]})
        elif self.was_created_by_order is True:
            if not self.course_run.course.targeted_by_products.exists():
                # --> *2
                message = _(
                    (
                        "The related course run is not linked to any product, "
                        "so it cannot be created in the scope of an order."
                    )
                )
                raise ValidationError({"was_created_by_order": [message]})

        return super().clean()

    def set(self):
        """Try setting the state to the LMS."""
        if not self.created_on:
            raise ValidationError(
                "The enrollment should be created before being set to the LMS."
            )

        # Now we can enroll user to LMS course run
        link = self.course_run.resource_link
        lms = LMSHandler.select_lms(link)
        state = enums.ENROLLMENT_STATE_SET

        if lms is None:
            # If no lms found we set enrollment and order to failure state
            # this issue could be due to a bad setting or a bad resource_link filled,
            # so we need to log this error to fix it quickly to joanie side
            logger.error('No LMS configuration found for course run: "%s".', link)
            state = enums.ENROLLMENT_STATE_FAILED
        else:
            # Try to enroll user to lms course run and update joanie's enrollment state
            try:
                lms.set_enrollment(self)
            except exceptions.EnrollmentError:
                logger.error(
                    'Enrollment failed for course run "%s".',
                    self.course_run.resource_link,
                )
                state = enums.ENROLLMENT_STATE_FAILED

        self.state = state
        Enrollment.objects.filter(pk=self.pk).update(state=state)

    def save(self, *args, **kwargs):
        """
        Call full clean before saving instance and sync enrollment active state
        with LMS if needed.
        """
        self.full_clean()
        is_creating = self.created_on is None

        super().save(*args, **kwargs)

        if is_creating is True and self.is_active is True:
            logger.info("Active Enrollment %s has been created", self.id)
            self.set()

        if self.is_active != self.last_is_active:
            # The user has changed their subscription status
            logger.info(
                "Enrollment %s has changed its active status to %s",
                self.id,
                self.is_active,
            )
            self.last_is_active = self.is_active
            self.set()
