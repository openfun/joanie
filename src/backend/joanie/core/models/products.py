"""
Declare and configure the models for the product / order part
"""

import itertools
import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

import requests
from django_fsm import FSMField, transition
from django_fsm.signals import post_transition
from parler import models as parler_models
from urllib3.util import Retry

from joanie.core import enums
from joanie.core.models.accounts import User
from joanie.core.models.base import BaseModel
from joanie.core.models.certifications import Certificate
from joanie.core.models.contracts import Contract
from joanie.core.models.courses import (
    Course,
    CourseProductRelation,
    CourseRun,
    CourseState,
    Enrollment,
    Organization,
)
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers, webhooks
from joanie.payment import get_payment_backend
from joanie.payment.models import CreditCard
from joanie.signature.backends import get_signature_backend

logger = logging.getLogger(__name__)

adapter = requests.adapters.HTTPAdapter(
    max_retries=Retry(
        total=4,
        backoff_factor=0.1,
        status_forcelist=[500],
        allowed_methods=["POST"],
    )
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


# pylint: disable=too-many-public-methods, too-many-lines
class Product(parler_models.TranslatableModel, BaseModel):
    """
    Product model represents detailed description of product to purchase for a course.
    All course runs and certification available for a product are defined here.
    """

    type = models.CharField(
        _("type"), choices=enums.PRODUCT_TYPE_CHOICES, max_length=50
    )
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255),
        description=models.CharField(_("description"), max_length=500, blank=True),
        instructions=models.TextField(_("instructions"), blank=True),
        call_to_action=models.CharField(_("call to action"), max_length=255),
    )
    target_courses = models.ManyToManyField(
        to=Course,
        related_name="targeted_by_products",
        through="ProductTargetCourseRelation",
        through_fields=("product", "course"),
        verbose_name=_("target courses"),
        blank=True,
    )
    price = models.DecimalField(
        _("price"),
        help_text=_("tax included"),
        decimal_places=2,
        default=0.00,
        max_digits=9,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )
    certificate_definition = models.ForeignKey(
        "CertificateDefinition",
        verbose_name=_("certificate definition"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    contract_definition = models.ForeignKey(
        "ContractDefinition",
        verbose_name=_("Contract definition"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "joanie_product"
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_on"]

    def __str__(self):
        return (
            f"[{self.type.upper()}] {self.safe_translation_getter('title', any_language=True)} "
            f"{self.price}"
        )

    @property
    def target_course_runs(self):
        """
        Retrieve all course runs related to the product instance.

        Returns:

            - all course runs related to target courses for which the product/course
              relation does not specify a list of eligible course runs (see course_runs
              field on the ProductTargetCourseRelation model)

            - only the course runs specified on the product/course relation for target
              courses on which a list of eligible course runs was specified on the
              product/course relation.

        """
        target_course_relations_with_course_runs = self.target_course_relations.filter(
            course_runs__isnull=False
        ).only("pk")

        return CourseRun.objects.filter(
            models.Q(product_relations__in=target_course_relations_with_course_runs)
            | models.Q(
                course__in=self.target_courses.exclude(
                    product_target_relations__in=target_course_relations_with_course_runs
                )
            )
        )

    def get_equivalent_course_run_data(self, visibility=None):
        """
        Return data for the virtual course run equivalent to this product when, taking
        into account all course runs targeted by the product if any.

        The dates (start, end, enrollment start and enrollment end) and languages of this
        equivalent course run are calculated based on the course runs of each course targeted
        by this product.

        If a product has no target courses or no related course runs, it will still return
        an equivalent course run with null dates and hidden visibility.
        """
        if self.type == enums.PRODUCT_TYPE_CERTIFICATE:
            return None

        dates = self.get_equivalent_course_run_dates()

        return {
            "catalog_visibility": visibility
            or (enums.COURSE_AND_SEARCH if any(dates.values()) else enums.HIDDEN),
            "languages": self.get_equivalent_course_run_languages(),
            # Get dates from aggregate
            **{
                key: value.isoformat() if value else None
                for key, value in dates.items()
            },
        }

    def get_equivalent_course_run_languages(self):
        """Return a list of distinct languages available in alphabetical order."""
        languages = self.target_course_runs.values_list(
            "languages", flat=True
        ).distinct()
        # Go through a set for uniqueness of each language then return an ordered list
        return sorted(set(itertools.chain.from_iterable(languages)))

    def get_equivalent_course_run_dates(self):
        """
        Return a dict of dates equivalent to course run dates
        by aggregating dates of all target course runs as follows:
        - start: Pick the earliest start date
        - end: Pick the latest end date
        - enrollment_start: Pick the latest enrollment start date
        - enrollment_end: Pick the earliest enrollment end date
        """
        aggregate = self.target_course_runs.aggregate(
            models.Min("start"),
            models.Max("end"),
            models.Max("enrollment_start"),
            models.Min("enrollment_end"),
        )

        return {key.split("__")[0]: value for key, value in aggregate.items()}

    @staticmethod
    def get_equivalent_serialized_course_runs_for_products(
        products, courses=None, visibility=None
    ):
        """
        Get the list of products to synchronize a product's related course runs

        visibility: [CATALOG_VISIBILITY_CHOICES]:
            If not None, force visibility for the synchronized products. Useful when
            synchronizing a product that does not have anymore course runs and should
            therefore be hidden.
        """
        equivalent_course_runs = []
        for product in products:
            course_run_data = product.get_equivalent_course_run_data(
                visibility=visibility
            )

            # Ignore products of type certificate
            if course_run_data is None:
                continue

            course_relations = product.course_relations.select_related("course")
            if courses:
                course_relations = course_relations.filter(course__in=courses)

            for relation in course_relations.iterator():
                equivalent_course_runs.append(
                    {
                        **course_run_data,
                        "resource_link": relation.uri,
                        "course": relation.course.code,
                    }
                )

        return equivalent_course_runs

    @property
    def state(self) -> str:
        """
        Process the state of the product based on its equivalent course run dates.
        """
        dates = self.get_equivalent_course_run_dates()
        return CourseRun.compute_state(**dates)

    def clean(self):
        """
        Allow certificate definition only for product with type credential or certificate.
        """
        if (
            self.certificate_definition
            and self.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ):
            raise ValidationError(
                _(
                    f"Certificate definition is only allowed for product kinds: "
                    f"{', '.join(enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED)}"
                )
            )
        super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class ProductTargetCourseRelation(BaseModel):
    """
    ProductTargetCourseRelation model allows to define position of each courses to follow
    for a product.
    """

    course = models.ForeignKey(
        to=Course,
        verbose_name=_("course"),
        related_name="product_target_relations",
        on_delete=models.RESTRICT,
    )
    product = models.ForeignKey(
        to=Product,
        verbose_name=_("product"),
        related_name="target_course_relations",
        on_delete=models.CASCADE,
    )
    # allow restricting what course runs are proposed
    # for a given course when a product is bought.
    course_runs = models.ManyToManyField(
        CourseRun,
        related_name="product_relations",
        verbose_name=_("course runs"),
        blank=True,
    )
    position = models.PositiveSmallIntegerField(_("position in product"), default=0)
    is_graded = models.BooleanField(
        _("take into account for certification"),
        help_text=_("Take into account the course grade for certification."),
        default=True,
    )

    class Meta:
        db_table = "joanie_product_target_course_relation"
        ordering = ("position", "course")
        unique_together = ("product", "course")
        verbose_name = _("Target course relation to a product with a position")
        verbose_name_plural = _("Target courses relations to products with a position")

    def __str__(self):
        return f"{self.product}: {self.position} / {self.course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """
        We need to synchronize with webhooks upon deletion. We could have used the signal but it
        also triggers on query deletes and is being called as many times as there are objects in
        the query. This would generate many separate calls to the webhook and would not scale. We
        decided to not provide synchronization for the moment on bulk deletes and leave it up to
        the developer to handle these cases correctly.
        """
        product = self.product
        super().delete(using=using, keep_parents=keep_parents)
        serialized_course_runs = (
            Product.get_equivalent_serialized_course_runs_for_products([product])
        )
        webhooks.synchronize_course_runs(serialized_course_runs)


class OrderGroup(BaseModel):
    """Order group to enforce a maximum number of seats for a product."""

    nb_seats = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Number of seats"),
        help_text=_(
            "The maximum number of orders that can be validated for a given order group"
        ),
    )
    course_product_relation = models.ForeignKey(
        to=CourseProductRelation,
        verbose_name=_("course product relation"),
        related_name="order_groups",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(_("is active"), default=True)

    def get_nb_binding_orders(self):
        """Query the number of binding orders related to this order group."""
        product_id = self.course_product_relation.product_id
        course_id = self.course_product_relation.course_id

        return self.orders.filter(
            models.Q(course_id=course_id)
            | models.Q(enrollment__course_run__course_id=course_id),
            product_id=product_id,
            state__in=enums.BINDING_ORDER_STATES,
        ).count()

    @property
    def can_edit(self):
        """Return True if the order group can be edited."""
        return not self.orders.exists()


class Order(BaseModel):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    organization = models.ForeignKey(
        to=Organization,
        verbose_name=_("organization"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    product = models.ForeignKey(
        to=Product,
        verbose_name=_("product"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )

    # Origin: either from a course or from an enrollment
    course = models.ForeignKey(
        to=Course,
        verbose_name=_("course"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    enrollment = models.ForeignKey(
        to=Enrollment,
        verbose_name=_("enrollment"),
        on_delete=models.PROTECT,
        related_name="related_orders",
        blank=True,
        null=True,
    )

    order_group = models.ForeignKey(
        OrderGroup,
        verbose_name=_("order group"),
        related_name="orders",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    target_courses = models.ManyToManyField(
        Course,
        related_name="target_orders",
        through="OrderTargetCourseRelation",
        through_fields=("order", "course"),
        verbose_name=_("courses"),
        blank=True,
    )
    total = models.DecimalField(
        _("price"),
        editable=False,
        help_text=_("tax included"),
        decimal_places=2,
        max_digits=9,
        default=0.00,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )
    owner = models.ForeignKey(
        to=User,
        verbose_name=_("owner"),
        related_name="orders",
        on_delete=models.RESTRICT,
        db_index=True,
    )
    has_consent_to_terms = models.BooleanField(
        verbose_name=_("has consent to terms"),
        editable=False,
        default=False,
        help_text=_("User has consented to the platform terms and conditions."),
    )
    state = FSMField(
        default=enums.ORDER_STATE_DRAFT,
        choices=enums.ORDER_STATE_CHOICES,
        db_index=True,
    )

    class Meta:
        db_table = "joanie_order"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "owner", "product"],
                condition=~models.Q(state=enums.ORDER_STATE_CANCELED),
                name="unique_owner_course_product_not_canceled",
                violation_error_message="An order for this product and course already exists.",
            ),
            models.UniqueConstraint(
                fields=["enrollment", "owner", "product"],
                condition=~models.Q(state=enums.ORDER_STATE_CANCELED),
                name="unique_owner_enrollment_product_not_canceled",
                violation_error_message="An order for this product and enrollment already exists.",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(("course__isnull", False), ("enrollment__isnull", True))
                    | models.Q(("course__isnull", True), ("enrollment__isnull", False))
                ),
                name="either_course_or_enrollment",
                violation_error_message="Order should have either a course or an enrollment",
            ),
            models.CheckConstraint(
                check=models.Q(state=enums.ORDER_STATE_DRAFT)
                | models.Q(organization__isnull=False),
                name="organization_required_if_not_draft",
                violation_error_message="Order should have an organization if not in draft state",
            ),
        ]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_on"]

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

    def can_be_state_validated(self):
        """
        An order can be validated if the product is free or if it
        has invoices.
        """
        return self.total == enums.MIN_ORDER_TOTAL_AMOUNT or self.invoices.count() > 0

    def can_be_state_submitted(self):
        """
        An order can be submitted if the order has a course, an organization,
        an owner, and a product
        """
        return (
            (self.course is not None or self.enrollment is not None)
            and self.organization is not None
            and self.owner is not None
            and self.product is not None
        )

    @transition(
        field="state",
        source=[enums.ORDER_STATE_DRAFT, enums.ORDER_STATE_PENDING],
        target=enums.ORDER_STATE_SUBMITTED,
        conditions=[can_be_state_submitted],
    )
    def _submit(self, billing_address=None, credit_card_id=None, request=None):
        """
        Transition order to submitted state.
        Create a payment if the product is fee
        """
        payment_backend = get_payment_backend()
        if credit_card_id:
            try:
                credit_card = CreditCard.objects.get(
                    owner=self.owner, id=credit_card_id
                )
                return payment_backend.create_one_click_payment(
                    request=request,
                    order=self,
                    billing_address=billing_address,
                    credit_card_token=credit_card.token,
                )
            except (CreditCard.DoesNotExist, NotImplementedError):
                pass
        payment_info = payment_backend.create_payment(
            request=request, order=self, billing_address=billing_address
        )

        return payment_info

    def submit(self, billing_address=None, credit_card_id=None, request=None):
        """
        Transition order to submitted state and to validate if order is free
        """
        if self.total != enums.MIN_ORDER_TOTAL_AMOUNT and billing_address is None:
            raise ValidationError({"billing_address": ["This field is required."]})

        if self.state == enums.ORDER_STATE_DRAFT:
            for relation in ProductTargetCourseRelation.objects.filter(
                product=self.product
            ):
                order_relation = OrderTargetCourseRelation.objects.create(
                    order=self,
                    course=relation.course,
                    position=relation.position,
                    is_graded=relation.is_graded,
                )
                order_relation.course_runs.set(relation.course_runs.all())

        if self.total == enums.MIN_ORDER_TOTAL_AMOUNT:
            self.validate()
            return None

        return self._submit(billing_address, credit_card_id, request)

    @transition(
        field="state",
        source=[
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_SUBMITTED,
        ],
        target=enums.ORDER_STATE_VALIDATED,
        conditions=[can_be_state_validated],
    )
    def validate(self):
        """
        Transition order to validated state.
        """

    @transition(
        field="state",
        source="*",
        target=enums.ORDER_STATE_CANCELED,
    )
    def cancel(self):
        """
        Mark order instance as "canceled".
        """

    @transition(
        field="state",
        source=[enums.ORDER_STATE_SUBMITTED, enums.ORDER_STATE_VALIDATED],
        target=enums.ORDER_STATE_PENDING,
    )
    def pending(self, payment_id=None):
        """
        Mark order instance as "pending" and abort the related
        payment if there is one
        """
        if payment_id:
            payment_backend = get_payment_backend()
            payment_backend.abort_payment(payment_id)

    @property
    def target_course_runs(self):
        """
        Retrieve all course runs related to the order instance.

        Returns:

            - all course runs related to target courses for which the product/course
              relation does not specify a list of eligible course runs (see course_runs
              field on the ProductTargetCourseRelation model)

            - only the course runs specified on the product/course relation for target
              courses on which a list of eligible course runs was specified on the
              product/course relation.
        """
        course_relations_with_course_runs = self.course_relations.filter(
            course_runs__isnull=False
        ).only("pk")

        return CourseRun.objects.filter(
            models.Q(order_relations__in=course_relations_with_course_runs)
            | models.Q(
                course__in=self.target_courses.exclude(
                    order_relations__in=course_relations_with_course_runs
                )
            )
        )

    @cached_property
    def main_invoice(self) -> dict | None:
        """
        Return main order's invoice.
        It corresponds to the only invoice related
        to the order without parent.
        """
        try:
            return self.invoices.get(parent__isnull=True)
        except ObjectDoesNotExist:
            return None

    # pylint: disable=too-many-branches
    # ruff: noqa: PLR0912
    def clean(self):
        """Clean instance fields and raise a ValidationError in case of issue."""
        error_dict = defaultdict(list)

        required_field, empty_field = enums.PRODUCT_TYPE_ORDER_FIELDS[self.product.type]
        if not getattr(self, required_field, None):
            error_dict[required_field].append(
                _(
                    f"{required_field} field should be set for {self.product.type} products."
                )
            )
        if getattr(self, empty_field, None):
            error_dict[empty_field].append(
                _(
                    f"{empty_field} field should be left empty for {self.product.type} products."
                )
            )

        if self.enrollment:
            if self.enrollment.user != self.owner:
                error_dict["enrollment"].append(
                    _("The enrollment should belong to the owner of this order.")
                )
            if self.enrollment.was_created_by_order:
                error_dict["enrollment"].append(
                    _(
                        "Orders can't be placed on enrollments originating from an order."
                    )
                )
            if (
                self.enrollment.course_run.course.state["priority"]
                >= CourseState.ARCHIVED_CLOSED
            ):
                error_dict["course"].append(
                    _(
                        "The order cannot be generated on course run that is in archived state."
                    )
                )

        # pylint: disable=no-member
        if not self.created_on and (self.enrollment or self.course) and self.product:
            course = self.course or self.enrollment.course_run.course
            course_title = course.title
            product_title = self.product.title

            try:
                filters = {"product": self.product_id, "course": course}
                if self.organization_id:
                    filters.update({"organizations": self.organization_id})
                course_product_relation = CourseProductRelation.objects.get(**filters)
            except ObjectDoesNotExist:
                course_product_relation = None
                if self.organization_id:
                    message = _(
                        f'This order cannot be linked to the product "{product_title}", '
                        f'the course "{course_title}" and '
                        f'the organization "{self.organization.title}".'
                    )
                else:
                    message = _(
                        f'This order cannot be linked to the product "{product_title}" and '
                        f'the course "{course_title}".'
                    )
                error_dict["__all__"].append(message)

            if (
                self.order_group_id
                and self.order_group.course_product_relation.product_id
                != self.product_id
                and self.order_group.course_product_relation.course != course
            ):
                error_dict["order_group"].append(
                    f"This order group does not apply to the product {product_title:s} "
                    f"and the course {course_title}."
                )

            if (
                course_product_relation
                and course_product_relation.order_groups.filter(is_active=True).exists()
            ):
                if not self.order_group_id or not self.order_group.is_active:
                    error_dict["order_group"].append(
                        f"An active order group is required for product {product_title:s}."
                    )
                else:
                    nb_seats = self.order_group.nb_seats
                    if 0 < nb_seats <= self.order_group.get_nb_binding_orders():
                        error_dict["order_group"].append(
                            f"Maximum number of orders reached for product {product_title:s}"
                        )

        if error_dict:
            raise ValidationError(error_dict)

        if not self.created_on:
            self.total = self.product.price

        super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_target_enrollments(self, is_active=None):
        """
        Retrieve owner's enrollments related to the ordered target courses.
        """
        filters = {
            "course_run__course__in": self.target_courses.all(),
            "user": self.owner,
        }
        if is_active is not None:
            filters.update({"is_active": is_active})

        return Enrollment.objects.filter(**filters)

    def enroll_user_to_course_run(self):
        """
        Enroll user to course runs that are the unique course run opened
        for enrollment on their course.
        """
        now = timezone.now()

        # Annotation queries for counting open course runs
        open_course_runs_count = models.Count(
            models.Case(
                models.When(
                    models.Q(course__course_runs__enrollment_end__gt=now)
                    | models.Q(course__course_runs__enrollment_end__isnull=True),
                    course__course_runs__enrollment_start__lte=now,
                    then=1,
                ),
                distinct=True,
                output_field=models.IntegerField(),
            )
        )
        open_specific_course_runs_count = models.Count(
            "course_runs",
            distinct=True,
            filter=(
                models.Q(course_runs__enrollment_end__gt=now)
                | models.Q(course_runs__enrollment_end__isnull=True)
            )
            & models.Q(course_runs__enrollment_start__lte=now),
        )

        # Annotation queries for retrieving open course runs
        open_course_run = CourseRun.objects.filter(
            models.Q(enrollment_end__gt=now) | models.Q(enrollment_end__isnull=True),
            enrollment_start__lte=now,
            course=models.OuterRef("course"),
        ).values("pk")[:1]

        open_specific_course_run = (
            OrderTargetCourseRelation.course_runs.through.objects.filter(
                models.Q(courserun__enrollment_end__gt=now)
                | models.Q(courserun__enrollment_end__isnull=True),
                courserun__enrollment_start__lte=now,
                ordertargetcourserelation_id=models.OuterRef("pk"),
            ).values("courserun_id")[:1]
        )

        # Main query
        course_relations_with_one_course_run = self.course_relations.annotate(
            nb_open_course_runs=open_course_runs_count,
            nb_open_specific_course_runs=open_specific_course_runs_count,
            nb_specific_course_runs=models.Count("course_runs", distinct=True),
            open_course_run_id=models.Subquery(open_course_run),
            open_specific_course_run_id=models.Subquery(open_specific_course_run),
        ).filter(
            models.Q(nb_open_specific_course_runs=1)
            | models.Q(nb_specific_course_runs=0, nb_open_course_runs=1)
        )

        for course_relation in course_relations_with_one_course_run:
            open_course_run_id = (
                course_relation.open_specific_course_run_id
                if course_relation.nb_open_specific_course_runs == 1
                else course_relation.open_course_run_id
            )
            try:
                enrollment = Enrollment.objects.only("is_active").get(
                    course_run_id=open_course_run_id, user=self.owner
                )
            except Enrollment.DoesNotExist:
                Enrollment.objects.create(
                    course_run_id=open_course_run_id,
                    is_active=True,
                    user=self.owner,
                    was_created_by_order=True,
                )
            else:
                if enrollment.is_active is False:
                    enrollment.is_active = True
                    enrollment.save()

    def unenroll_user_from_course_runs(self):
        """
        Unenroll user from all active course runs related to the order instance.
        There are two cases where user will not be unenrolled :
            - When `course_run.is_listed` is True, that means
              this course run is available for free.
            - The course run is targeted by another product
              also owned by the order owner.
        """
        # Unroll user to all active enrollment related to the order
        enrollments = self.get_target_enrollments(is_active=True).select_related(
            "course_run"
        )

        for enrollment in enrollments:
            # If course run is not available for free
            if not enrollment.course_run.is_listed:
                # If order owner does not own another product which contains the course run
                owns_other_products = (
                    enrollment.course_run.course.targeted_by_products.filter(
                        orders__in=self.owner.orders.exclude(
                            state=enums.ORDER_STATE_CANCELED
                        )
                    )
                    .exclude(pk=self.product.pk)
                    .exists()
                )
                if not owns_other_products:
                    enrollment.is_active = False
                    enrollment.save()

    def get_or_generate_certificate(self):
        """
        Return the certificate for this order if it exists. Otherwise, check if the
        order is eligible for certification then generate certificate if it is.

        Eligibility means that order contains
        one passed enrollment per graded courses.

        Return:
            instance[Certificate], False: if a certificate pre-existed for the current order
            instance[Certificate], True: if a certificate has been generated for the current order
            None, False: if the order is not eligible for certification
        """
        try:
            return Certificate.objects.get(order=self), False
        except Certificate.DoesNotExist:
            pass

        if (
            not self.product.certificate_definition
            or self.product.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ):
            return None, False

        if self.product.type == enums.PRODUCT_TYPE_CERTIFICATE:
            graded_courses = [self.enrollment.course_run.course_id]
        else:
            graded_courses = (
                self.target_courses.filter(order_relations__is_graded=True)
                .order_by("order_relations__position")
                .prefetch_related("course_runs")
            )
        graded_courses_count = len(graded_courses)

        if graded_courses_count == 0:
            return None, False

        # Retrieve all enrollments in one query. Since these enrollments rely on
        # order course runs, the count will always be pretty small.
        course_enrollments = Enrollment.objects.filter(
            course_run__course__in=graded_courses,
            course_run__is_gradable=True,
            course_run__start__lte=timezone.now(),
            is_active=True,
            user=self.owner,
        ).select_related("user", "course_run")

        # If we do not have one enrollment per graded course, there is no need to
        # continue, we are sure that order is not eligible for certification.
        if len(course_enrollments) != graded_courses_count:
            return None, False

        # Otherwise, we now need to know if each enrollment has been passed
        for enrollment in course_enrollments:
            if enrollment.is_passed is False:
                # If one enrollment has not been passed, no need to continue,
                # We are sure that order is not eligible for certification.
                return None, False

        return (
            Certificate.objects.create(
                order=self,
                organization=self.organization,
                certificate_definition=self.product.certificate_definition,
            ),
            True,
        )

    # pylint: disable=no-member
    def submit_for_signature(self, user: User):
        """
        When the product has a contract definition, it prepares the order's contract.
        If needed we prepare a new contract or we retrieve the existing one. Then, we check
        the document's validity, and we check if the context has not changed since last submission.
        If the document's validity as been reached, or the context has changed, we need
        to delete at the signature provider the ongoing procedure and create a new contract
        to submit.
        """
        if not self.product.contract_definition_id:
            message = "No contract definition attached to the contract's product."
            logger.error(
                message,
                extra={
                    "context": {
                        "order": self.to_dict(),
                        "product": self.product.to_dict(),
                    }
                },
            )
            raise ValidationError(message)

        if self.state != enums.ORDER_STATE_VALIDATED:
            message = "Cannot submit an order that is not yet validated."
            logger.error(message, extra={"context": {"order": self.to_dict()}})
            raise ValidationError(message)

        contract_definition = self.product.contract_definition

        try:
            contract = self.contract
        except Contract.DoesNotExist:
            contract = Contract(order=self, definition=contract_definition)

        if self.contract and self.contract.student_signed_on:
            message = "Contract is already signed by the student, cannot resubmit."
            logger.error(
                message, extra={"context": {"contract": self.contract.to_dict()}}
            )
            raise PermissionDenied(message)

        backend_signature = get_signature_backend()
        context = contract_definition_utility.generate_document_context(
            contract_definition=contract_definition,
            user=user,
            order=contract.order,
        )
        file_bytes = issuers.generate_document(
            name=contract_definition.name, context=context
        )

        was_already_submitted = (
            contract.submitted_for_signature_on and contract.signature_backend_reference
        )
        should_be_resubmitted = was_already_submitted and (
            not contract.is_eligible_for_signing() or contract.context != context
        )

        if should_be_resubmitted:
            backend_signature.delete_signing_procedure(
                contract.signature_backend_reference
            )

        # We want to submit or re-submit the contract for signature in three cases:
        # 1- the contract was never submitted for signature before
        # 2- the contract was submitted for signature but the user did not sign it in time
        #    before expiration of the signature workflow
        # 3- the contract context has changed since it was last submitted for signature
        if should_be_resubmitted or not was_already_submitted:
            reference, checksum = backend_signature.submit_for_signature(
                title=contract_definition.title,
                file_bytes=file_bytes,
                order=self,
            )
            contract.tag_submission_for_signature(reference, checksum, context)

        return backend_signature.get_signature_invitation_link(
            user.email, [contract.signature_backend_reference]
        )

    def get_equivalent_course_run_dates(self):
        """
        Return a dict of dates equivalent to course run dates
        by aggregating dates of all target course runs as follows:
        - start: Pick the earliest start date
        - end: Pick the latest end date
        - enrollment_start: Pick the latest enrollment start date
        - enrollment_end: Pick the earliest enrollment end date
        """
        aggregate = self.target_course_runs.aggregate(
            models.Min("start"),
            models.Max("end"),
            models.Max("enrollment_start"),
            models.Min("enrollment_end"),
        )

        return {
            key.split("__")[0]: value if value else None
            for key, value in aggregate.items()
        }


@receiver(post_transition, sender=Order)
def order_post_transition_callback(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Post transition callback for Order model. When an order is validated,
    it automatically enrolls user and when it is canceled, it automatically
    unenrolls user.
    """
    instance.save()
    # Only enroll user if the product has no contract to sign, otherwise we should wait
    # for the contract to be signed before enrolling the user.
    if (
        instance.state == enums.ORDER_STATE_VALIDATED
        and instance.product.contract_definition is None
    ):
        instance.enroll_user_to_course_run()

    if instance.state == enums.ORDER_STATE_CANCELED:
        instance.unenroll_user_from_course_runs()

    # When an order is validated, if the user was previously enrolled for free in any of the
    # course runs targeted by the purchased product, we should change their enrollment mode on
    # these course runs to "verified".
    if instance.state in [enums.ORDER_STATE_VALIDATED, enums.ORDER_STATE_CANCELED]:
        for enrollment in Enrollment.objects.filter(
            course_run__course__target_orders=instance
        ).select_related("course_run", "user"):
            enrollment.set()

    if order_enrollment := instance.enrollment:
        # Trigger LMS synchronization for source enrollment to update mode
        # Make sure it is saved in case the state is modified e.g in case of synchronization
        # failure
        order_enrollment.set()

    # Reset course product relation cache if its representation is impacted by changes
    # on related orders
    # e.g. number of remaining seats when an order group is used
    # see test_api_course_product_relation_read_detail_with_order_groups_cache
    if instance.order_group:
        course_id = instance.course_id or instance.enrollment.course_run.course_id
        CourseProductRelation.objects.filter(
            product_id=instance.product_id, course_id=course_id
        ).update(updated_on=timezone.now())


class OrderTargetCourseRelation(BaseModel):
    """
    OrderTargetCourseRelation model allows to define position of each courses to follow
    for an order.
    """

    course = models.ForeignKey(
        to=Course,
        verbose_name=_("course"),
        related_name="order_relations",
        on_delete=models.RESTRICT,
    )
    course_runs = models.ManyToManyField(
        CourseRun,
        verbose_name=_("course runs"),
        related_name="order_relations",
        blank=True,
    )
    order = models.ForeignKey(
        to=Order,
        verbose_name=_("order"),
        related_name="course_relations",
        on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField(_("position in order"))
    is_graded = models.BooleanField(
        _("take into account for certification"),
        help_text=_("Take into account the course grade for certification."),
        default=True,
    )

    class Meta:
        db_table = "joanie_order_target_course_relation"
        ordering = ("position", "course")
        unique_together = ("order", "course")
        verbose_name = _("Course relation to an order with a position")
        verbose_name_plural = _("Courses relations to orders with a position")

    def __str__(self):
        return f"{self.order}: {self.position} / {self.course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)
