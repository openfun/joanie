"""
Declare and configure the models for the product / order part
"""

import itertools
import logging
import uuid
from collections import defaultdict
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

import requests
from django_countries.fields import CountryField
from parler import models as parler_models
from stockholm import Money
from urllib3.util import Retry

from joanie.core import enums, utils
from joanie.core.exceptions import CertificateGenerationError
from joanie.core.fields.schedule import (
    OrderPaymentScheduleDecoder,
    OrderPaymentScheduleEncoder,
)
from joanie.core.flows.batch_order import BatchOrderFlow
from joanie.core.flows.order import OrderFlow
from joanie.core.models.accounts import Address, User
from joanie.core.models.activity_logs import ActivityLog
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
from joanie.core.utils import (
    contract_definition as contract_definition_utility,
)
from joanie.core.utils import (
    get_default_currency_symbol,
    issuers,
    webhooks,
)
from joanie.core.utils.billing_address import CompanyBillingAddress
from joanie.core.utils.contract_definition import embed_images_in_context
from joanie.core.utils.course_run.aggregate_course_runs_dates import (
    aggregate_course_runs_dates,
)
from joanie.core.utils.discount import calculate_price
from joanie.core.utils.payment_schedule import generate as generate_payment_schedule
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
    certification_level = models.PositiveSmallIntegerField(
        verbose_name=_("level of certification"),
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text=_(
            "Level of certification as defined by the European Qualifications Framework."
        ),
        blank=True,
        null=True,
    )
    teachers = models.ManyToManyField(
        to="Teacher",
        related_name="products",
        verbose_name=_("teachers"),
        help_text=_("Teachers that will be displayed on the delivered certificate."),
        blank=True,
    )
    skills = models.ManyToManyField(
        to="Skill",
        related_name="products",
        verbose_name=_("skills"),
        help_text=_("Skills that will be displayed on the delivered certificate."),
        blank=True,
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

        The offer properties may vary according to the product price. If the product is not free,
        we don't want to set explicitly a price.

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
            **self.get_equivalent_course_run_offer(),
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
            self.target_course_runs,
            ignore_archived=ignore_archived,
        )

    def get_equivalent_course_run_offer(self):
        """
        Return the offer properties for the equivalent course run.
        If the product is a certificate, we bind offer information into
        certificate_offer properties otherwise we bind into offer properties.

        Furthermore, if the product is free, we don't want to set explicitly a price.
        """

        fields = {"offer": "offer", "price": "price"}

        if self.type == enums.PRODUCT_TYPE_CERTIFICATE:
            fields = {"offer": "certificate_offer", "price": "certificate_price"}

        if self.price == 0:
            return {fields["offer"]: enums.COURSE_OFFER_FREE}

        return {
            fields["offer"]: enums.COURSE_OFFER_PAID,
            fields["price"]: self.price,
            "price_currency": settings.DEFAULT_CURRENCY,
        }

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

    @staticmethod
    def get_serialized_certificated_course_runs(
        products, courses=None, certifying=True
    ):
        """
        Return a list of serialized course runs related to
        the given certificate products.

        visibility: [CATALOG_VISIBILITY_CHOICES]:
            If not None, force visibility for the synchronized products. Useful when
            synchronizing a product that does not have anymore course runs and should
            therefore be hidden.
        """
        serialized_course_runs = []
        now = timezone.now()

        for product in products:
            if product.type != enums.PRODUCT_TYPE_CERTIFICATE:
                continue

            courses = courses or product.courses.all()
            course_runs = CourseRun.objects.filter(course__in=courses, end__gt=now)

            serialized_course_runs.extend(
                [
                    course_run.get_serialized(certifying=certifying)
                    for course_run in course_runs
                ]
            )

        return serialized_course_runs

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


class OrderGroupManager(models.Manager):
    """Custom manager for the OrderGroup model."""

    def find_actives(self, course_product_relation_id):
        """
        Retrieve all active order groups for a given course product relation,
        ordered by position.
        """
        return (
            super()
            .get_queryset()
            .filter(
                is_active=True,
                course_product_relation_id=course_product_relation_id,
            )
            .order_by("position")
        )


class OrderGroup(BaseModel):
    """Order group to enforce a maximum number of seats for a product."""

    objects = OrderGroupManager()

    nb_seats = models.PositiveSmallIntegerField(
        default=None,
        verbose_name=_("Number of seats"),
        help_text=_(
            "The maximum number of orders that can be validated for a given order group"
        ),
        null=True,
        blank=True,
    )
    course_product_relation = models.ForeignKey(
        to=CourseProductRelation,
        verbose_name=_("course product relation"),
        related_name="order_groups",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(_("is active"), default=True)
    position = models.PositiveSmallIntegerField(
        _("priority"),
        help_text=_("Priority"),
        default=None,
        null=True,
        blank=True,
    )
    start = models.DateTimeField(
        help_text=_("Date at which the order group rule starts"),
        verbose_name=_("rule starts at"),
        blank=True,
        null=True,
    )
    end = models.DateTimeField(
        help_text=_("Date at which the order group rule ends"),
        verbose_name=_("rule ends at"),
        blank=True,
        null=True,
    )
    discount = models.ForeignKey(
        to="Discount",
        verbose_name=_("Product price discount"),
        related_name="order_groups",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    description = models.CharField(
        _("description"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Description of the order group"),
    )

    class Meta:
        verbose_name = _("Order group")
        verbose_name_plural = _("Order groups")
        ordering = ["course_product_relation", "position"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start__lte=models.F("end")),
                name="check_start_before_end",
                violation_error_message=_("Start date cannot be greater than end date"),
            ),
        ]

    def get_nb_binding_orders(self):
        """Query the number of binding orders related to this order group."""
        product_id = self.course_product_relation.product_id
        course_id = self.course_product_relation.course_id

        return self.orders.filter(
            models.Q(course_id=course_id)
            | models.Q(enrollment__course_run__course_id=course_id),
            product_id=product_id,
            state__in=enums.ORDER_STATES_BINDING,
        ).count()

    def get_nb_to_own_orders(self):
        """Query the number of orders that are in `to_own` state related to this order group."""
        return self.orders.filter(
            course_id=self.course_product_relation.course_id,
            product_id=self.course_product_relation.product_id,
            state=enums.ORDER_STATE_TO_OWN,
        ).count()

    @property
    def can_edit(self):
        """Return True if the order group can be edited."""
        return not self.orders.exists()

    @property
    def available_seats(self) -> int | None:
        """Return the number of available seats on the order group, or None if unlimited."""
        if self.nb_seats is None:
            return None

        used_seats = self.get_nb_binding_orders() + self.get_nb_to_own_orders()
        return self.nb_seats - used_seats

    @property
    def is_enabled(self):
        """
        Returns boolean whether the order group is enabled based on its activation status
        and time constraints.
        """
        if not self.is_active:
            return False

        now = timezone.now()
        start = self.start or now
        end = self.end or now

        return start <= now <= end

    @property
    def is_assignable(self):
        """
        Returns boolean whether the order group is enabled, and have available seats.
        """
        return self.is_enabled and self.available_seats != 0

    def save(self, *args, **kwargs):
        """
        Override save method to assign the next available position number
        within its course product relation if not already set.
        """
        if not self.created_on and self.position is None:
            self.position = self.course_product_relation.order_groups.count()

        # clear product relation cache
        logger.debug(
            "Clearing caches from order group for course product relation %s",
            self.course_product_relation_id,
        )
        self.course_product_relation.clear_cache()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """
        Override delete method to clear the cache of the course product relation
        and to synchronize with webhooks.
        """
        # clear product relation cache
        logger.debug(
            "Clearing caches from order group for course product relation %s",
            self.course_product_relation_id,
        )
        self.course_product_relation.clear_cache()
        super().delete(using=using, keep_parents=keep_parents)

    def set_position(self, position):
        """
        Set the position of the order group and update the positions of other order groups
        in the same course product relation accordingly.
        """
        if position == self.position:
            return  # Nothing to do

        # Get count and normalize position within valid range (0 to count-1)
        count = OrderGroup.objects.filter(
            course_product_relation_id=self.course_product_relation_id
        ).count()
        position = max(0, min(position, count - 1))

        old_position = self.position

        with transaction.atomic():
            if old_position < position:
                # Moving down - shift intermediate items up
                OrderGroup.objects.filter(
                    course_product_relation_id=self.course_product_relation_id,
                    position__gt=old_position,
                    position__lte=position,
                ).update(position=models.F("position") - 1)
            else:
                # Moving up - shift intermediate items down
                OrderGroup.objects.filter(
                    course_product_relation_id=self.course_product_relation_id,
                    position__lt=old_position,
                    position__gte=position,
                ).update(position=models.F("position") + 1)

            # Update this order group's position
            self.position = position
            self.save(update_fields=["position"])


class OrderManager(models.Manager):
    """Custom manager for the Order model."""

    def find_installments(self, due_date):
        """Retrieve orders with a payment schedule containing a due date."""
        return (
            super()
            .get_queryset()
            .filter(payment_schedule__contains=[{"due_date": due_date.isoformat()}])
        )

    def find_pending_installments(self):
        """Retrieve orders with at least one pending installment."""
        return (
            super()
            .get_queryset()
            .filter(
                state__in=[
                    enums.ORDER_STATE_PENDING,
                    enums.ORDER_STATE_PENDING_PAYMENT,
                ],
                payment_schedule__contains=[{"state": enums.PAYMENT_STATE_PENDING}],
            )
        )

    def find_installments_to_pay(self):
        """Retrieve orders with at least one installment to pay."""
        return self.find_pending_installments().union(
            self.filter(
                state__in=[
                    enums.ORDER_STATE_PENDING,
                    enums.ORDER_STATE_PENDING_PAYMENT,
                ],
                payment_schedule__contains=[{"state": enums.PAYMENT_STATE_ERROR}],
            )
        )

    def get_stuck_signing_orders(self):
        """
        Retrieve orders stuck in the `to_sign` or `signing` states that are
        beyond the tolerated time limit of last update.
        """
        return (
            super()
            .get_queryset()
            .filter(
                state__in=[
                    enums.ORDER_STATE_TO_SIGN,
                    enums.ORDER_STATE_SIGNING,
                ],
                updated_on__lte=timezone.now()
                - timedelta(
                    seconds=settings.JOANIE_ORDER_UPDATE_DELAY_LIMIT_IN_SECONDS
                ),
            )
        )

    def get_stuck_certificate_payment_orders(self):
        """
        Retrieve orders stuck in the `to_save_payment_method` state for
        products of type certificate that are beyond the tolerated
        time limit of last update.
        """
        return (
            super()
            .get_queryset()
            .filter(
                product__type=enums.PRODUCT_TYPE_CERTIFICATE,
                state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                updated_on__lte=timezone.now()
                - timedelta(
                    seconds=settings.JOANIE_ORDER_UPDATE_DELAY_LIMIT_IN_SECONDS
                ),
            )
        )


class Order(BaseModel):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    objects = OrderManager()

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
    order_groups = models.ManyToManyField(
        OrderGroup,
        verbose_name=_("order group"),
        related_name="orders",
        blank=True,
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
        null=True,
        blank=True,
    )
    _has_consent_to_terms = models.BooleanField(
        verbose_name=_("has consent to terms"),
        editable=False,
        default=False,
        help_text=_("User has consented to the platform terms and conditions."),
        db_column="has_consent_to_terms",
    )
    has_waived_withdrawal_right = models.BooleanField(
        verbose_name=_("has waived their right of withdrawal"),
        editable=False,
        default=False,
        help_text=_("User has waived their withdrawal right."),
    )
    state = models.CharField(
        default=enums.ORDER_STATE_DRAFT,
        choices=enums.ORDER_STATE_CHOICES,
        db_index=True,
    )
    payment_schedule = models.JSONField(
        _("payment schedule"),
        help_text=_("Payment schedule for the order."),
        editable=False,
        blank=True,
        null=True,
        encoder=OrderPaymentScheduleEncoder,
        decoder=OrderPaymentScheduleDecoder,
        default=list,
    )
    credit_card = models.ForeignKey(
        to="payment.CreditCard",
        verbose_name=_("credit card"),
        related_name="orders",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    voucher = models.ForeignKey(
        to="Voucher",
        verbose_name=_("voucher"),
        related_name="orders",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    batch_order = models.ForeignKey(
        to="BatchOrder",
        verbose_name=_("batch_order"),
        related_name="orders",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "joanie_order"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "owner", "product"],
                condition=~models.Q(state__in=enums.ORDER_INACTIVE_STATES),
                name="unique_owner_course_product_not_canceled_or_not_in_refund_states",
                violation_error_message="An order for this product and course already exists.",
            ),
            models.UniqueConstraint(
                fields=["enrollment", "owner", "product"],
                condition=~models.Q(state__in=enums.ORDER_INACTIVE_STATES),
                name="unique_owner_enrollment_product_not_canceled_or_not_in_refund_states",
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

    def __init__(self, *args, **kwargs):
        """Initiate Order object"""
        super().__init__(*args, **kwargs)
        self.flow = OrderFlow(self)

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

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
        if self.enrollment:
            return CourseRun.objects.filter(enrollments=self.enrollment)

        course_relations_with_course_runs = self.course_relations.filter(
            course_runs__isnull=False
        ).only("pk")
        target_courses_without_course_runs_subset = self.target_courses.exclude(
            order_relations__in=course_relations_with_course_runs
        )

        return CourseRun.objects.filter(
            models.Q(order_relations__in=course_relations_with_course_runs)
            | models.Q(course__in=target_courses_without_course_runs_subset)
        ).distinct()

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

    @property
    def is_free(self):
        """
        Return True if the order is free.
        """
        return not self.total

    @property
    def has_payment_method(self):
        """
        Return True if the order has a payment method.
        """
        return (
            self.credit_card is not None
            and self.credit_card.initial_issuer_transaction_identifier is not None
        )

    @property
    def has_contract(self):
        """
        Return True if the order has a contract.
        """
        try:
            return self.contract is not None  # pylint: disable=no-member
        except Contract.DoesNotExist:
            return False

    @property
    def has_submitted_contract(self):
        """
        Return True if the order has a submitted contract.
        Which means a contract in the process of being signed
        """
        try:
            return self.contract.submitted_for_signature_on is not None  # pylint: disable=no-member
        except Contract.DoesNotExist:
            return False

    @property
    def has_unsigned_contract(self):
        """
        Return True if the order has an unsigned contract.
        """
        try:
            return self.contract.student_signed_on is None  # pylint: disable=no-member
        except Contract.DoesNotExist:
            return self.product.contract_definition is not None

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
                not self.created_on and self.state not in [enums.ORDER_STATE_CANCELED]
            ) and (
                self.enrollment.course_run.course.state["priority"]
                >= CourseState.ARCHIVED_CLOSED
            ):
                error_dict["course"].append(
                    _(
                        "The order cannot be created on course run that is in archived state."
                    )
                )

        if self.voucher and not self.created_on:
            if not self.voucher.is_usable_by(self.owner.id):
                error_dict["voucher"].append(_("The voucher is not usable."))

        if error_dict:
            raise ValidationError(error_dict)

        super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_discounted_price(self):
        """
        Return the total price considering the order group discount if it exists. Else, if
        there is no order group, the total price should be the full product price.
        """
        if self.voucher:
            discount = self.voucher.discount or self.voucher.order_group.discount
            if discount:
                return calculate_price(self.product.price, discount)

        for order_group in self.order_groups.all():
            if discount := order_group.discount:
                return calculate_price(self.product.price, discount)

        return self.product.price

    def freeze_total(self):
        """
        Freeze the total of the order.
        """
        self.total = self.get_discounted_price()
        self.save()

    def get_target_enrollments(self, is_active=None):
        """
        Retrieve owner's enrollments related to the ordered target courses.
        """
        if self.enrollment:
            filters = {"pk": self.enrollment_id}
        else:
            filters = {
                "course_run__in": self.target_course_runs,
                "user": self.owner,
            }
        if is_active is not None:
            filters.update({"is_active": is_active})

        return Enrollment.objects.filter(**filters)

    def freeze_target_courses(self):
        """
        Freeze target courses of the order.
        """
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
            # The user should not be enrolled in another opened course run of the same course.
            course_run = CourseRun.objects.get(id=open_course_run_id)
            if course_run.can_enroll(self.owner):
                enrollment, _ = Enrollment.objects.get_or_create(
                    course_run_id=open_course_run_id,
                    user=self.owner,
                    defaults={"was_created_by_order": True, "is_active": True},
                )
            else:
                raise ValidationError(
                    _(
                        f"Cannot automatically enroll the user {self.owner.id} in the course"
                        f"run for the course '{course_run.course.title}' because there is "
                        " already an active enrollment on that course on an opened course run."
                    )
                )
            if not enrollment.is_active:
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
            CertificateGenerationError: if the order is not eligible to get a certificate generated
            with the reason why.
        """
        try:
            return Certificate.objects.get(order=self), False
        except Certificate.DoesNotExist:
            pass

        if (
            not self.product.certificate_definition
            or self.product.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ):
            # pylint:disable=no-member
            raise CertificateGenerationError(
                _(
                    f"Product {self.product.title} does not allow to generate a certificate."
                ),
            )

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
            raise CertificateGenerationError(_("No graded courses found."))

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
            raise CertificateGenerationError(
                _("This order is not ready for gradation.")
            )

        # Otherwise, we now need to know if each enrollment has been passed
        for enrollment in course_enrollments:
            if enrollment.is_passed is False:
                # If one enrollment has not been passed, no need to continue,
                # We are sure that order is not eligible for certification.
                raise CertificateGenerationError(
                    _(
                        "Course run "
                        f"{enrollment.course_run.course.title}-{enrollment.course_run.title}"
                        " has not been passed."
                    ),
                )

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

        if self.state not in [enums.ORDER_STATE_TO_SIGN, enums.ORDER_STATE_SIGNING]:
            message = "Cannot submit an order that is not to sign."
            logger.error(message, extra={"context": {"order": self.to_dict()}})
            raise ValidationError(message)

        contract_definition = self.product.contract_definition

        if self.contract.student_signed_on:
            message = "Contract is already signed by the student, cannot resubmit."
            logger.error(
                message, extra={"context": {"contract": self.contract.to_dict()}}
            )
            raise PermissionDenied(message)

        backend_signature = get_signature_backend()
        context = contract_definition_utility.generate_document_context(
            contract_definition=contract_definition,
            user=user,
            order=self.contract.order,
        )
        context_with_images = embed_images_in_context(context)
        file_bytes = issuers.generate_document(
            name=contract_definition.name, context=context_with_images
        )

        was_already_submitted = (
            self.contract.submitted_for_signature_on
            and self.contract.signature_backend_reference
        )
        should_be_resubmitted = was_already_submitted and (
            not self.contract.is_eligible_for_signing()
            or self.contract.context != context
        )

        if should_be_resubmitted:
            backend_signature.delete_signing_procedure(
                self.contract.signature_backend_reference
            )

        # We want to submit or re-submit the contract for signature in three cases:
        # 1- the contract was never submitted for signature before
        # 2- the contract was submitted for signature but the user did not sign it in time
        #    before expiration of the signature workflow
        # 3- the contract context has changed since it was last submitted for signature
        if should_be_resubmitted or not was_already_submitted:
            now = timezone.now()
            course_code = (
                self.course.code
                if self.course
                else self.enrollment.course_run.course.code
            )
            reference, checksum = backend_signature.submit_for_signature(
                title=f"{now.strftime('%Y-%m-%d')}_{course_code}_{self.pk}",
                file_bytes=file_bytes,
                order=self,
            )
            self.contract.tag_submission_for_signature(reference, checksum, context)

        return backend_signature.get_signature_invitation_link(
            user.email, [self.contract.signature_backend_reference]
        )

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
            self.target_course_runs,
            ignore_archived=ignore_archived,
        )

    def get_schedule_dates(self):
        """
        Return the schedule dates for the order.
        The schedules date are based on contract sign date or the time the schedule is generated
        (right now) and the start and the end of the course run.
        """
        error_message = None
        course_run_dates = self.get_equivalent_course_run_dates(ignore_archived=True)
        start_date = course_run_dates["start"]
        end_date = course_run_dates["end"]

        if not end_date or not start_date:
            error_message = "Cannot retrieve start or end date for order"
            logger.error(
                error_message,
                extra={"context": {"order": self.to_dict()}},
            )
            raise ValidationError(error_message)

        if self.has_contract and not self.has_unsigned_contract:
            signing_date = self.contract.student_signed_on
        else:
            signing_date = timezone.now()

        return signing_date, start_date, end_date

    def generate_schedule(self):
        """
        Generate payment schedule installments for the order.
        When the order's product type is 'credential', there should always be more than 1
        installment. Whereas, when the order's product type is 'certificate', there should always
        be 1 installment only.
        """
        if self.product.type == enums.PRODUCT_TYPE_CREDENTIAL:
            beginning_contract_date, course_start_date, course_end_date = (
                self.get_schedule_dates()
            )
            self.payment_schedule = generate_payment_schedule(
                self.total, beginning_contract_date, course_start_date, course_end_date
            )
        else:
            self.payment_schedule = [
                {
                    "id": uuid.uuid4(),
                    "due_date": timezone.now().date(),
                    "amount": Money(self.total),
                    "state": enums.PAYMENT_STATE_PENDING,
                }
            ]

        self.save()

        return self.payment_schedule

    def _set_installment_state(self, installment_id, state):
        """
        Set the state of an installment in the payment schedule.

        Returns a set of boolean values to indicate if the installment is the first one, and if it
        is the last one.
        """
        for installment in self.payment_schedule:
            if installment["id"] == installment_id:
                installment["state"] = state
                self.save(update_fields=["payment_schedule"])
                self.flow.update()
                return
        raise ValueError(f"Installment with id {installment_id} not found")

    def set_installment_paid(self, installment_id):
        """
        Set the state of an installment to paid in the payment schedule.
        """
        ActivityLog.create_payment_succeeded_activity_log(self)
        self._set_installment_state(installment_id, enums.PAYMENT_STATE_PAID)

    def set_installment_refused(self, installment_id):
        """
        Set the state of an installment to refused in the payment schedule.
        """
        ActivityLog.create_payment_failed_activity_log(self)
        self._set_installment_state(installment_id, enums.PAYMENT_STATE_REFUSED)

    def set_installment_refunded(self, installment_id):
        """
        Set the state of an installment to `refunded` in the payment schedule.
        """
        ActivityLog.create_payment_refunded_activity_log(self)

        for installment in self.payment_schedule:
            if (
                installment["id"] == installment_id
                and installment["state"] == enums.PAYMENT_STATE_PAID
            ):
                installment["state"] = enums.PAYMENT_STATE_REFUNDED
                self.save(update_fields=["payment_schedule"])
                return
        raise ValueError(f"Installment with id {installment_id} cannot be refund")

    def set_installment_error(self, installment_id):
        """
        Set the state of an installment to `error` in the payment schedule.
        """
        self._set_installment_state(installment_id, enums.PAYMENT_STATE_ERROR)

    def cancel_remaining_installments(self):
        """
        Cancel all remaining installments in the payment schedule.
        """
        if not self.payment_schedule:
            return

        for installment in self.payment_schedule:
            if installment["state"] in enums.PAYMENT_STATES_TO_PAY:
                installment["state"] = enums.PAYMENT_STATE_CANCELED
        self.save(update_fields=["payment_schedule"])

    def get_first_installment_refused(self):
        """
        Retrieve the first installment that is refused in payment schedule of an order.
        """
        return next(
            (
                installment
                for installment in self.payment_schedule
                if installment["state"] == enums.PAYMENT_STATE_REFUSED
            ),
            None,
        )

    def withdraw(self):
        """
        Withdraw the order.
        """
        if not self.payment_schedule:
            raise ValidationError("No payment schedule found for this order")

        # check if current date is greater than the first installment due date
        if timezone.now().date() >= self.payment_schedule[0]["due_date"]:
            raise ValidationError(
                "Cannot withdraw order after the first installment due date"
            )

        self.flow.cancel()

    @property
    def has_consent_to_terms(self):
        """Redefine `has_consent_to_terms` property to raise an exception if used"""
        raise DeprecationWarning(
            "Access denied to has_consent_to_terms: deprecated field"
        )

    def _get_address(self, billing_address):
        """
        Returns an Address instance for a billing address.
        """
        if not billing_address:
            raise ValidationError("Billing address is required for non-free orders.")

        address, _ = Address.objects.get_or_create(
            **billing_address,
            defaults={
                "owner": self.owner,
                "is_reusable": False,
                "title": f"Billing address of order {self.id}",
            },
        )
        return address

    def _create_main_invoice(self, billing_address):
        """
        Create the main invoice for the order.
        """
        address = self._get_address(billing_address)
        Invoice = apps.get_model("payment", "Invoice")  # pylint: disable=invalid-name
        Invoice.objects.get_or_create(
            order=self,
            defaults={"total": self.total, "recipient_address": address},
        )

    def init_flow(self, billing_address=None):
        """
        Transition order to assigned state, creates an invoice if needed and call the flow update.
        """
        self.freeze_total()
        self.flow.assign()
        if not self.is_free:
            self._create_main_invoice(billing_address)

        self.freeze_target_courses()

        if self.product.contract_definition and not self.has_contract:
            Contract.objects.create(
                order=self, definition=self.product.contract_definition
            )

        self.flow.update()

    def get_date_next_installment_to_pay(self):
        """Get the next due date of installment to pay in the payment schedule."""
        return next(
            (
                installment["due_date"]
                for installment in self.payment_schedule
                if installment["state"] in enums.PAYMENT_STATES_TO_DEBIT
            ),
            None,
        )

    def get_installment_index(self, state, find_first=False):
        """
        Retrieve the index of the first or last occurrence of an installment in the
        payment schedule based on the input parameter payment state.
        """
        position = None
        for index, entry in enumerate(self.payment_schedule, start=0):
            if entry["state"] == state:
                position = index
                if find_first:
                    break
        return position

    def get_remaining_balance_to_pay(self):
        """Get the amount of installments remaining to pay in the payment schedule."""
        return Money.sum(
            installment["amount"]
            for installment in self.payment_schedule
            if installment["state"] in enums.PAYMENT_STATES_TO_PAY
        )

    def get_amount_installments_refunded(self):
        """Get the amount of installments that were refunded in the payment schedule."""
        return Money.sum(
            installment["amount"]
            for installment in self.payment_schedule
            if installment["state"] == enums.PAYMENT_STATE_REFUNDED
        )

    @property
    def discount(self):
        """
        Return the discount applied to the order.
        It can be either from a voucher or an order group.
        """
        for order_group in self.order_groups.all():
            if discount := order_group.discount:
                description = order_group.description or ""
                initial_price = f"{self.product.price} {get_default_currency_symbol()}"
                return f"{discount} ({initial_price}) {description}"

        return None


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


class BatchOrder(BaseModel):
    """
    BatchOrder allows to define a batch of orders to prepare.
    """

    class Meta:
        db_table = "joanie_batch_order"
        verbose_name = _("batch order")
        verbose_name_plural = _("batch orders")
        ordering = ["created_on"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    state__in=[
                        enums.BATCH_ORDER_STATE_DRAFT,
                        enums.BATCH_ORDER_STATE_CANCELED,
                    ]
                )
                | models.Q(organization__isnull=False),
                name="required_organization_if_not_draft_or_canceled",
                violation_error_message=(
                    "BatchOrder requires organization unless in draft or cancel states."
                ),
            )
        ]

    relation = models.ForeignKey(
        to=CourseProductRelation,
        verbose_name=_("course product relation batch orders"),
        related_name="batch_orders",
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        to=Organization,
        verbose_name=_("organization"),
        related_name="batch_orders",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    voucher = models.ForeignKey(
        to="Voucher",
        verbose_name=_("voucher"),
        related_name="batch_orders",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    contract = models.ForeignKey(
        to=Contract,
        help_text=_("contract of type convention"),
        verbose_name=_("contract"),
        related_name="batch_orders",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        to=User,
        verbose_name=_("owner"),
        related_name="batch_orders",
        help_text=_("eligible person to sign the convention from the company"),
        on_delete=models.RESTRICT,
        db_index=True,
    )
    identification_number = models.CharField(
        verbose_name=_("company identification number"),
        help_text=_("company identification number like SIRET in France"),
        max_length=255,
    )
    company_name = models.CharField(
        verbose_name=_("company name"),
        help_text=_("company name"),
        max_length=255,
    )
    address = models.CharField(
        verbose_name=_("address"), help_text=_("company address"), max_length=255
    )
    postcode = models.CharField(
        verbose_name=_("postcode"), help_text=_("company postcode"), max_length=50
    )
    city = models.CharField(
        verbose_name=_("city"), help_text=_("company city"), max_length=255
    )
    country = CountryField(verbose_name=_("company country"))
    nb_seats = models.PositiveSmallIntegerField(
        verbose_name=_("Number of seats"),
        help_text=_("The number of seats to reserve"),
        default=1,
        validators=[MinValueValidator(1)],
    )
    trainees = models.JSONField(
        verbose_name=_("trainees"),
        help_text=_("trainees name list"),
        editable=True,
        encoder=DjangoJSONEncoder,
        default=list,
    )
    total = models.DecimalField(
        _("total"),
        editable=False,
        help_text=_("total price for orders"),
        decimal_places=2,
        max_digits=9,
        default=0.00,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )
    state = models.CharField(
        default=enums.BATCH_ORDER_STATE_DRAFT,
        choices=enums.BATCH_ORDER_STATE_CHOICES,
        db_index=True,
    )
    order_groups = models.ManyToManyField(
        OrderGroup,
        verbose_name=_("order group"),
        related_name="batch_orders",
        blank=True,
    )

    # pylint:disable=no-member
    def clean(self):
        """
        Ensure that the number of reserved seats (`nb_seats`) matches the number of trainees
        in the `trainees` list when saving a BatchOrder instance.
        """
        if len(self.trainees) != self.nb_seats:
            raise ValidationError(
                _("The number of trainees must match the number of seats.")
            )

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initiate Batch Order object"""
        super().__init__(*args, **kwargs)
        self.flow = BatchOrderFlow(self)

    def init_flow(self):
        """
        Transition batch order to assigned state, creates a main invoice,
        generates a contract.
        """
        self.freeze_total()
        self.create_main_invoice()

        # Generate the contract
        if self.relation.product.contract_definition and not self.contract:
            self.contract = Contract.objects.create(
                definition=self.relation.product.contract_definition
            )
        self.flow.update()
        self.save()

    def get_discounted_price(self):
        """
        When a voucher is used, return the discounted price. Otherwise, return the total price,
        considering the order group discount if applicable. If neither a voucher nor an order
        group discount exists, return the total amount based on the number of seats taken.
        """
        price_per_seat = Money(self.relation.product.price).as_decimal()
        total = self.nb_seats * price_per_seat

        if self.voucher:
            discount = self.voucher.discount or self.voucher.order_group.discount
            if discount:
                return calculate_price(total, discount)

        for order_group in self.order_groups.all():
            if discount := order_group.discount:
                return calculate_price(total, discount)

        return total

    def freeze_total(self):
        """
        Freeze the total price for the batch order.
        """
        self.total = self.get_discounted_price()
        self.save(update_fields=["total"])

    # pylint: disable=no-member
    def submit_for_signature(self, user: User):
        """
        Submit the contract of type convention to signature if it has not been submitted yet.
        In the cases where it has been submitted to signature but it has not been signed yet,
        if the context has changed, we will resubmit the refresh version of the contract
        of type convention. Also, if the document's validity has been reached, we will resubmit
        a newer version for it to be eligble to be signed.
        """
        if not self.relation.product.contract_definition_id:
            message = "No contract definition attached to the contract's product."
            logger.error(
                message,
                extra={
                    "context": {
                        "batch_order": self.to_dict(),
                        "relation__product": self.relation.product.to_dict(),
                    }
                },
            )
            raise ValidationError(message)

        if not self.is_assigned:
            raise ValidationError(
                _(
                    f"Your batch order cannot be submitted for signature, state: {self.state}"
                )
            )

        if self.is_signed_by_owner:
            message = "Contract is already signed by the buyer, cannot resubmit."
            logger.error(
                message, extra={"context": {"contract": self.contract.to_dict()}}
            )
            raise PermissionDenied(message)

        contract_definition = self.relation.product.contract_definition
        context = contract_definition_utility.generate_document_context(
            contract_definition=contract_definition,
            user=user,
            batch_order=self,
        )
        context_with_images = embed_images_in_context(context)
        file_bytes = issuers.generate_document(
            name=contract_definition.name, context=context_with_images
        )

        was_already_submitted = (
            self.contract.submitted_for_signature_on
            and self.contract.signature_backend_reference
        )
        should_be_resubmitted = was_already_submitted and (
            not self.contract.is_eligible_for_signing()
            or self.contract.context != context
        )

        backend_signature = get_signature_backend()

        if should_be_resubmitted:
            backend_signature.delete_signing_procedure(
                self.contract.signature_backend_reference
            )

        if should_be_resubmitted or not was_already_submitted:
            now = timezone.now()
            reference, checksum = backend_signature.submit_for_signature(
                title=f"{now.strftime('%Y-%m-%d')}_{self.relation.course.code}_{self.pk}",
                file_bytes=file_bytes,
                order=self,
            )
            self.contract.tag_submission_for_signature(reference, checksum, context)
            self.flow.update()

        return backend_signature.get_signature_invitation_link(
            self.owner.email, [self.contract.signature_backend_reference]
        )

    def generate_orders(self):
        """
        Generate orders and vouchers once the batch order has been paid.
        """
        if not self.is_paid:
            message = "The batch order is not yet paid."
            logger.error(
                message,
                extra={
                    "context": {
                        "batch_order": self.to_dict(),
                        "relation": self.relation.to_dict(),
                    }
                },
            )
            raise ValidationError(message)

        discount, _ = Discount.objects.get_or_create(rate=1)

        for _ in range(self.nb_seats):
            order = Order.objects.create(
                owner=None,
                product=self.relation.product,
                course=self.relation.course,
                organization=self.organization,
            )
            if self.order_groups.exists():
                order.order_groups.add(self.order_groups.first())

            order.voucher = Voucher.objects.create(
                discount=discount, multiple_use=False, multiple_users=False
            )
            order.flow.assign()
            self.orders.add(order)
            order.flow.update()

    @property
    def vouchers(self):
        """Return the exhaustive list of voucher codes generated from the orders"""
        return [order.voucher.code for order in self.orders.all()]

    @property
    def is_assigned(self):
        """Return boolean value whether the batch order is assigned to an organization"""
        return self.organization is not None

    @property
    def is_eligible_to_get_sign(self):
        """Return boolean value whether the batch order contract can be signed"""
        return self.state in [
            enums.BATCH_ORDER_STATE_ASSIGNED,
            enums.BATCH_ORDER_STATE_TO_SIGN,
        ]

    @property
    def is_submitted_to_signature(self):
        """Return boolean value whether the batch order contract is submitted to signature"""
        return (
            self.contract.student_signed_on is None
            and self.contract.submitted_for_signature_on is not None
        )

    @property
    def is_signed_by_owner(self):
        """Return boolean value whether the batch order contract is signed by the owner"""
        return (
            self.contract
            and self.contract.submitted_for_signature_on is not None
            and self.contract.student_signed_on is not None
        )

    @property
    def is_ready_for_payment(self):
        """Return boolean value whether the batch order can be submitted to payment"""
        return self.is_signed_by_owner is True and self.state in [
            enums.BATCH_ORDER_STATE_SIGNING,
            enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
        ]

    @property
    def is_eligible_to_validate_payment(self):
        """Return boolean value whether we can validate the payment of the batch order"""
        return self.state in [
            enums.BATCH_ORDER_STATE_SIGNING,
            enums.BATCH_ORDER_STATE_PENDING,
        ]

    @property
    def is_paid(self):
        """
        Return boolean value whether the batch order is fully paid. We should find the child
        invoice, and if present, the transaction linked to it should exist.
        """
        child_invoice = self.invoices.filter(
            batch_order=self, parent=self.main_invoice, total=0
        ).first()

        if not child_invoice:
            return False

        return child_invoice.transactions.filter(invoice=child_invoice).exists()

    @property
    def has_orders_generated(self):
        """Return boolean value whether the batch order has the orders generated"""
        return self.orders.exists()

    def cancel_orders(self):
        """
        Cancel all orders associated with this batch order and delete their linked vouchers.
        """
        if self.state != enums.BATCH_ORDER_STATE_CANCELED:
            message = "You must cancel the batch order before canceling the orders"
            logger.error(
                message,
                extra={
                    "context": {
                        "batch_order": self.to_dict(),
                    }
                },
            )
            raise ValidationError(message)

        for order in self.orders.all():
            order.voucher.delete()
            order.voucher = None
            order.flow.cancel()

    def create_billing_address(self):
        """
        Create a billing address for the batch order
        """
        return CompanyBillingAddress(
            address=self.address,
            postcode=self.postcode,
            city=self.city,
            country=self.country,
            language=self.owner.language,
            first_name=self.owner.first_name,
            last_name="",
        )

    def create_main_invoice(self):
        """
        Create the main invoice for the batch order.
        """
        Invoice = apps.get_model("payment", "Invoice")  # pylint: disable=invalid-name
        Invoice.objects.create(batch_order=self, total=self.total)

    @cached_property
    def main_invoice(self) -> dict | None:
        """
        Return main batch_order's invoice. It corresponds to the only invoice related
        to the batch order without parent.
        """
        try:
            return self.invoices.get(parent__isnull=True)
        except ObjectDoesNotExist:
            return None


class Skill(parler_models.TranslatableModel, BaseModel):
    """
    Skill model allows to define a skill that can be associated to a product.
    """

    class Meta:
        db_table = "joanie_skill"
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ["created_on"]

    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255),
    )

    def _check_title_uniqueness(self):
        """Check that the title being save does not exist in the active language."""
        language_code = get_language()

        if (
            Skill.objects.annotate(lower_title=Lower("translations__title"))
            .filter(
                lower_title=self.title.lower(),  # pylint: disable=no-member
                translations__language_code=language_code,
            )
            .exists()
        ):
            raise ValidationError(_("A skill with this title already exists."))

    def clean(self):
        """Sanitize title then ensure its uniqueness before saving."""
        self.title = utils.remove_extra_whitespaces(self.title)  # pylint: disable=attribute-defined-outside-init
        self._check_title_uniqueness()

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class Teacher(BaseModel):
    """
    Teacher model allows to define a teacher that can be associated to a product.
    """

    class Meta:
        db_table = "joanie_teacher"
        verbose_name = _("Teacher")
        verbose_name_plural = _("Teachers")
        ordering = ["last_name", "first_name"]
        unique_together = ("first_name", "last_name")

    first_name = models.CharField(_("first name"), max_length=255)
    last_name = models.CharField(_("last name"), max_length=255)


class Discount(BaseModel):
    """
    Discount model allows to define a discount on a price.
    """

    class Meta:
        db_table = "joanie_discount"
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")
        ordering = ["created_on"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rate__isnull=False) | models.Q(amount__isnull=False),
                name="discount_rate_or_amount_required",
                violation_error_message="Discount rate or amount is required.",
            ),
            models.CheckConstraint(
                check=models.Q(rate__isnull=True) | models.Q(amount__isnull=True),
                name="discount_rate_and_amount_exclusive",
                violation_error_message="Discount rate and amount are exclusive.",
            ),
        ]

    amount = models.PositiveSmallIntegerField(
        _("amount"),
        help_text=_("Discount amount"),
        null=True,
        blank=True,
        unique=True,
    )
    rate = models.FloatField(
        _("rate"),
        help_text=_("Discount rate"),
        null=True,
        blank=True,
        unique=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.rate is not None:
            rate_as_int = int(self.rate * 100)
            return f"-{rate_as_int}%"

        return f"-{self.amount} {get_default_currency_symbol()}"

    @property
    def usage_count(self):
        """
        Returns the count of how many times a discount is used through order groups
        and vouchers.
        """
        return self.order_groups.count() + self.vouchers.count()


def generate_random_code():
    """Generate a random unique code for vouchers."""
    while True:
        code = get_random_string(18)
        if not Voucher.objects.filter(code=code).exists():
            return code


class Voucher(BaseModel):
    """
    Voucher model allows to define a voucher that can be associated to an order group and used
    by a user to get a discount or access to a product.
    """

    class Meta:
        db_table = "joanie_voucher"
        verbose_name = _("Voucher")
        verbose_name_plural = _("Vouchers")
        ordering = ["created_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "order_group"],
                name="unique_code_order_group",
                violation_error_message=(
                    "A voucher with this code already exists for this order group."
                ),
            ),
            models.CheckConstraint(
                check=models.Q(discount__isnull=False)
                | models.Q(order_group__isnull=False),
                name="voucher_discount_or_order_group_required",
                violation_error_message="Voucher discount or order group is required.",
            ),
        ]

    code = models.CharField(
        _("code"),
        help_text=_("Voucher code"),
        max_length=255,
        default=generate_random_code,
    )
    order_group = models.ForeignKey(
        to=OrderGroup,
        verbose_name=_("order group"),
        related_name="vouchers",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    discount = models.ForeignKey(
        to=Discount,
        verbose_name=_("discount"),
        related_name="vouchers",
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    multiple_use = models.BooleanField(
        _("multiple use"),
        help_text=_("Voucher can be used multiple times per user."),
        default=False,
    )
    multiple_users = models.BooleanField(
        _("multiple users"),
        help_text=_("Voucher can be used by multiple users."),
        default=False,
    )

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code or str(self.order_group)

    def is_usable_by(self, user_id):
        """
        Depending on the voucher configuration, check if the voucher can be used by the user.
        """
        # Voucher can be used multiple times by multiple users
        if self.multiple_use and self.multiple_users:
            return True

        orders_queryset = self.orders.exclude(
            state__in=enums.ORDER_STATES_VOUCHER_CLAIMABLE
        )

        # Voucher can be used multiple times but only by one user
        if self.multiple_use:
            return not orders_queryset.exclude(owner_id=user_id).exists()

        # Voucher can be used by multiple users but only once per user
        if self.multiple_users:
            return not orders_queryset.filter(owner_id=user_id).exists()

        # Voucher can be used only once by one user
        return not orders_queryset.exists()
