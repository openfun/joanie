"""
Declare and configure the models for the product / order part
"""
import itertools
import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist, ValidationError
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
from joanie.core.models.certifications import Certificate
from joanie.core.utils import webhooks
from joanie.payment import get_payment_backend
from joanie.payment.models import CreditCard

from . import accounts as accounts_models
from . import courses as courses_models
from .base import BaseModel

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
        call_to_action=models.CharField(_("call to action"), max_length=255),
    )
    target_courses = models.ManyToManyField(
        to=courses_models.Course,
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

        return courses_models.CourseRun.objects.filter(
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
        return sorted(list(set(itertools.chain.from_iterable(languages))))

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
                        "resource_link": relation.get_read_detail_api_url(),
                        "course": relation.course.code,
                    }
                )

        return equivalent_course_runs

    @property
    def state(self):
        """
        Process the state of the product based on its equivalent course run dates.
        """
        dates = self.get_equivalent_course_run_dates()
        return courses_models.CourseRun.compute_state(**dates)

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


class ProductTargetCourseRelation(BaseModel):
    """
    ProductTargetCourseRelation model allows to define position of each courses to follow
    for a product.
    """

    course = models.ForeignKey(
        to=courses_models.Course,
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
        courses_models.CourseRun,
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


class Order(BaseModel):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    organization = models.ForeignKey(
        to=courses_models.Organization,
        verbose_name=_("organization"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        to=Product,
        verbose_name=_("product"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )

    # Origin: either from a course or from an enrollment
    course = models.ForeignKey(
        to=courses_models.Course,
        verbose_name=_("course"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    enrollment = models.ForeignKey(
        to=courses_models.Enrollment,
        verbose_name=_("enrollment"),
        on_delete=models.PROTECT,
        related_name="related_orders",
        blank=True,
        null=True,
    )

    target_courses = models.ManyToManyField(
        courses_models.Course,
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
        to=accounts_models.User,
        verbose_name=_("owner"),
        related_name="orders",
        on_delete=models.RESTRICT,
        db_index=True,
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
                name="unique_owner_product_not_canceled",
                violation_error_message="An order for this product and course already exists.",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(("course__isnull", False), ("enrollment__isnull", True))
                    | models.Q(("course__isnull", True), ("enrollment__isnull", False))
                ),
                name="either_course_or_enrollment",
                violation_error_message="Order should have either a course or an enrollment",
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
        return self.total == 0.0 or self.invoices.count() > 0

    def can_be_state_submitted(self):
        """
        An order can be submitted if the order has a course, an organization,
        an owner, and a product
        """
        return (
            self.course is not None
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
        if self.total != 0.0 and billing_address is None:
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

        if self.total == 0.0:
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

        return courses_models.CourseRun.objects.filter(
            models.Q(order_relations__in=course_relations_with_course_runs)
            | models.Q(
                course__in=self.target_courses.exclude(
                    order_relations__in=course_relations_with_course_runs
                )
            )
        )

    @cached_property
    def main_invoice(self):
        """
        Return main order's invoice.
        It corresponds to the only invoice related
        to the order without parent.
        """
        try:
            return self.invoices.get(parent__isnull=True)
        except ObjectDoesNotExist:
            return None

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

        course_product_relation = (
            courses_models.CourseProductRelation.objects.filter(
                course=self.course_id,
                product=self.product_id,
                organizations=self.organization_id,
            )
            .only("max_validated_orders")
            .first()
        )
        if (
            not self.created_on
            and self.course_id
            and self.product_id
            and self.organization_id
            and course_product_relation is None
        ):
            # pylint: disable=no-member
            message = _(
                f'The course "{self.course.title}" and the product "{self.product.title}" '
                f'should be linked for organization "{self.organization.title}".'
            )
            error_dict["__all__"].append(message)

        if course_product_relation is not None:
            max_validated_orders = course_product_relation.max_validated_orders
        else:
            max_validated_orders = 0
        if max_validated_orders > 0:
            annotation = (
                Order.objects.filter(
                    product=self.product,
                    course=self.course,
                    state__in=(enums.ORDER_STATE_VALIDATED, enums.ORDER_STATE_PENDING),
                )
                .annotate(
                    orders_count=models.Count("id", distinct=True),
                )
                .values("orders_count")
                .first()
                or {}
            )
            validated_order_count = annotation.get("orders_count", 0)
            if validated_order_count >= max_validated_orders:
                # pylint: disable=no-member
                message = _(
                    f"Maximum number of orders reached for product {self.product.title}"
                    f" and course {self.course.code}"
                )
                error_dict["max_validated_orders"].append(message)

        if error_dict:
            raise ValidationError(error_dict)

        if not self.created_on:
            self.total = self.product.price

        super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        models.Model.save(self, *args, **kwargs)

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

        return courses_models.Enrollment.objects.filter(**filters)

    def enroll_user_to_course_run(self):
        """
        Enroll user to course runs that are the unique course run opened
        for enrollment on their course.
        """
        courses_with_one_course_run = self.target_courses.annotate(
            course_runs_count=models.Count("course_runs")
        ).filter(
            models.Q(course_runs__enrollment_end__gt=timezone.now())
            | models.Q(course_runs__enrollment_end__isnull=True),
            course_runs__enrollment_start__lte=timezone.now(),
            course_runs_count=1,
        )

        for course in courses_with_one_course_run:
            course_run = course.course_runs.first()
            try:
                enrollment = courses_models.Enrollment.objects.only("is_active").get(
                    course_run=course_run, user=self.owner
                )
            except courses_models.Enrollment.DoesNotExist:
                courses_models.Enrollment.objects.create(
                    course_run=course_run,
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
        course_enrollments = courses_models.Enrollment.objects.filter(
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


@receiver(post_transition, sender=Order)
def order_post_transition_callback(
    sender, instance, **kwargs
):  # pylint: disable=unused-argument
    """
    Post transition callback for Order model. When an order is validated,
    it automatically enrolls user and when it is canceled, it automatically
    unenrolls user.
    """
    instance.save()
    if instance.state == enums.ORDER_STATE_VALIDATED:
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


class OrderTargetCourseRelation(BaseModel):
    """
    OrderTargetCourseRelation model allows to define position of each courses to follow
    for an order.
    """

    course = models.ForeignKey(
        to=courses_models.Course,
        verbose_name=_("course"),
        related_name="order_relations",
        on_delete=models.RESTRICT,
    )
    course_runs = models.ManyToManyField(
        courses_models.CourseRun,
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
