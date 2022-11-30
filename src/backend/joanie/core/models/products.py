"""
Declare and configure the models for the productorder_s part
"""
import logging
from decimal import Decimal as D

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from djmoney.models.fields import MoneyField
from djmoney.models.validators import MinMoneyValidator
from parler import models as parler_models

from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.core.models.certifications import Certificate
from joanie.lms_handler import LMSHandler

from .. import enums
from . import accounts as customers_models
from . import courses as courses_models
from .base import BaseModel

logger = logging.getLogger(__name__)


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
        courses_models.Course,
        related_name="targeted_by_products",
        through="ProductCourseRelation",
        verbose_name=_("target courses"),
        blank=True,
    )
    price = MoneyField(
        _("price"),
        max_digits=9,
        help_text=_("tax included"),
        decimal_places=2,
        default=D("0.00"),
        default_currency=settings.DEFAULT_CURRENCY,
        blank=True,
        validators=[
            MinMoneyValidator(0),
        ],
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
              field on the ProductCourseRelation model)

            - only the course runs specified on the product/course relation for target
              courses on which a list of eligible course runs was specified on the
              product/course relation.

        """
        course_relations_with_course_runs = self.course_relations.filter(
            course_runs__isnull=False
        ).only("pk")

        return courses_models.CourseRun.objects.filter(
            Q(product_relations__in=course_relations_with_course_runs)
            | Q(
                course__in=self.target_courses.exclude(
                    product_relations__in=course_relations_with_course_runs
                )
            )
        )

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


class ProductCourseRelation(BaseModel):
    """
    ProductCourseRelation model allows to define position of each courses to follow
    for a product.
    """

    course = models.ForeignKey(
        to=courses_models.Course,
        verbose_name=_("course"),
        related_name="product_relations",
        on_delete=models.RESTRICT,
    )
    product = models.ForeignKey(
        to=Product,
        verbose_name=_("product"),
        related_name="course_relations",
        on_delete=models.CASCADE,
    )
    course_runs = models.ManyToManyField(
        courses_models.CourseRun,
        verbose_name=_("course runs"),
        related_name="product_relations",
        blank=True,
    )
    position = models.PositiveSmallIntegerField(_("position in product"))
    is_graded = models.BooleanField(
        _("take into account for certification"),
        help_text=_("Take into account the course grade for certification."),
        default=True,
    )

    class Meta:
        db_table = "joanie_product_course_relation"
        ordering = ("position", "course")
        unique_together = ("product", "course")
        verbose_name = _("Course relation to a product with a position")
        verbose_name_plural = _("Courses relations to products with a position")

    def __str__(self):
        return f"{self.product}: {self.position} / {self.course}"


def on_add_course_runs_to_product_course_relation(action, instance, pk_set, **kwargs):
    """
    Signal triggered when course runs are added to a product course relation.
    Some checks are processed before course runs are linked to product course relation :
        1. Check that course runs linked are related to the relation course
    """
    if action != "pre_add":
        return

    # Instance can be a `ProductCourseRelation` or a `CourseRun`. In the case instance
    # is a CourseRun, we have to retrieve manually product course relations instances.
    if isinstance(instance, ProductCourseRelation):
        relations = [instance]
        course_runs_set = pk_set
    else:
        relations = ProductCourseRelation.objects.filter(pk__in=pk_set).select_related(
            "course__course_runs"
        )
        course_runs_set = {instance.pk}

    for relation in relations:
        # Check that all involved course runs rely on the relation course
        if relation.course.course_runs.filter(pk__in=course_runs_set).count() != len(
            course_runs_set
        ):
            raise ValidationError(
                {
                    "course_runs": [
                        (
                            "Limiting a course to targeted course runs can only be done"
                            " for course runs already belonging to this course."
                        )
                    ]
                }
            )


m2m_changed.connect(
    on_add_course_runs_to_product_course_relation,
    sender=ProductCourseRelation.course_runs.through,
)


class Order(BaseModel):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    course = models.ForeignKey(
        to=courses_models.Course,
        verbose_name=_("course"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        to=Product,
        verbose_name=_("product"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    target_courses = models.ManyToManyField(
        courses_models.Course,
        related_name="orders",
        through="OrderCourseRelation",
        verbose_name=_("courses"),
        blank=True,
    )
    total = MoneyField(
        _("total"),
        editable=False,
        max_digits=9,
        decimal_places=2,
        default=D("0.00"),
        default_currency=settings.DEFAULT_CURRENCY,
        blank=True,
        validators=[
            MinMoneyValidator(0),
        ],
    )
    owner = models.ForeignKey(
        to=customers_models.User,
        verbose_name=_("owner"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    is_canceled = models.BooleanField(_("is canceled"), default=False, editable=False)

    class Meta:
        db_table = "joanie_order"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "owner", "product"],
                condition=models.Q(is_canceled=False),
                name="unique_owner_product_not_canceled",
            )
        ]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_on"]

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

    @property
    def state(self):
        """
        Return order state.
        If order has been explicitly canceled, return canceled state.
        Then if order is free or has a related pro forma invoice, return validated state
        Otherwise return pending state.
        """
        if self.is_canceled is True:
            return enums.ORDER_STATE_CANCELED

        if (
            self.total.amount == 0  # pylint: disable=no-member
            or self.proforma_invoices.count() > 0
        ):
            return enums.ORDER_STATE_VALIDATED

        return enums.ORDER_STATE_PENDING

    @property
    def target_course_runs(self):
        """
        Retrieve all course runs related to the order instance.

        Returns:

            - all course runs related to target courses for which the product/course
              relation does not specify a list of eligible course runs (see course_runs
              field on the ProductCourseRelation model)

            - only the course runs specified on the product/course relation for target
              courses on which a list of eligible course runs was specified on the
              product/course relation.
        """
        course_relations_with_course_runs = self.course_relations.filter(
            course_runs__isnull=False
        ).only("pk")

        return courses_models.CourseRun.objects.filter(
            Q(order_relations__in=course_relations_with_course_runs)
            | Q(
                course__in=self.target_courses.exclude(
                    order_relations__in=course_relations_with_course_runs
                )
            )
        )

    @cached_property
    def main_proforma_invoice(self):
        """
        Return main order's pro forma invoice.
        It corresponds to the only pro forma invoice related
        to the order without parent.
        """
        try:
            return self.proforma_invoices.get(parent__isnull=True)
        except ObjectDoesNotExist:
            return None

    def clean(self):
        """Clean instance fields and raise a ValidationError in case of issue."""
        if (
            not self.created_on
            and self.course_id
            and self.product_id
            and not self.product.courses.filter(id=self.course_id).exists()
        ):
            # pylint: disable=no-member
            message = _(
                f'The product "{self.product.title}" is not linked to '
                f'course "{self.course.title}".'
            )
            raise ValidationError({"__all__": [message]})

        if not self.created_on:
            self.total = self.product.price

        return super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        is_new = not bool(self.created_on)
        models.Model.save(self, *args, **kwargs)
        if is_new:
            # - Generate order course relation
            for relation in ProductCourseRelation.objects.filter(product=self.product):
                order_relation = OrderCourseRelation.objects.create(
                    order=self,
                    course=relation.course,
                    position=relation.position,
                    is_graded=relation.is_graded,
                )
                order_relation.course_runs.set(relation.course_runs.all())

            self.validate()

    def validate(self):
        """
        Automatically enroll user to courses with only one course run.
        """
        if self.state != enums.ORDER_STATE_VALIDATED:
            return

        # Enroll user to course run that are the only one course run of the course
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
                enrollment = Enrollment.objects.get(
                    course_run=course_run, user=self.owner
                ).only("is_active")
            except Enrollment.DoesNotExist:
                Enrollment.objects.create(
                    course_run=course_run,
                    is_active=True,
                    user=self.owner,
                )
            else:
                if enrollment.is_active is False:
                    enrollment.is_active = True
                    enrollment.save()

    def get_enrollments(self, is_active=None):
        """
        Retrieve owner's enrollments related to the order courses.
        """
        filters = {
            "course_run__course__in": self.target_courses.all(),
            "user": self.owner,
        }
        if is_active is not None:
            filters.update({"is_active": is_active})

        return Enrollment.objects.filter(**filters)

    def cancel(self):
        """
        Mark order instance as "canceled".

        Then unenroll user from all active course runs related to the order instance.
        There are two cases where user will not be unenrolled :
            - When `course_run.is_listed` is True, that means
              this course run is available for free.
            - The course run is targeted by another product
              also owned by the order owner.
        """
        # Unroll user to all active enrollment related to the order
        enrollments = self.get_enrollments(is_active=True).select_related("course_run")

        for enrollment in enrollments:
            # If course run is not available for free
            if not enrollment.course_run.is_listed:
                # If order owner does not own another product which contains the course run
                owns_other_products = (
                    enrollment.course_run.course.targeted_by_products.filter(
                        orders__in=self.owner.orders.filter(is_canceled=False)
                    )
                    .exclude(pk=self.product.pk)
                    .exists()
                )
                if not owns_other_products:
                    enrollment.is_active = False
                    enrollment.save()

        self.is_canceled = True
        self.save()

    def create_certificate(self):
        """
        Create a certificate if the related product type is certifying and if one
        has not been already created.
        """
        if self.product.type not in enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED:
            raise ValidationError(
                _(
                    (
                        "Try to generate a certificate for "
                        f"a non-certifying product ({self.product})."
                    )
                )
            )

        if Certificate.objects.filter(order=self).exists():
            raise ValidationError(
                _(
                    (
                        "A certificate has been already issued for "  # pylint: disable=no-member
                        f"the order {self.id} "
                        f"on {self.certificate.issued_on}."
                    )
                )
            )

        Certificate.objects.create(
            order=self,
            certificate_definition=self.product.certificate_definition,
        )


class OrderCourseRelation(BaseModel):
    """
    OrderCourseRelation model allows to define position of each courses to follow
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
        db_table = "joanie_order_course_relation"
        ordering = ("position", "course")
        unique_together = ("order", "course")
        verbose_name = _("Course relation to an order with a position")
        verbose_name_plural = _("Courses relations to orders with a position")

    def __str__(self):
        return f"{self.order}: {self.position} / {self.course}"


class Enrollment(BaseModel):
    """
    Enrollment model represents and records lms enrollment state for course run
    as part of an order
    """

    course_run = models.ForeignKey(
        to=courses_models.CourseRun,
        verbose_name=_("course run"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    user = models.ForeignKey(
        to=customers_models.User,
        verbose_name=_("user"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    is_active = models.BooleanField(
        help_text="Tick to enroll the user to the course run.",
        verbose_name="is active",
    )
    state = models.CharField(
        _("state"), choices=enums.ENROLLMENT_STATE_CHOICES, max_length=50, blank=True
    )

    class Meta:
        db_table = "joanie_enrollment"
        unique_together = ("course_run", "user")
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

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
                except GradeError:
                    pass
                else:
                    cache.set(
                        self.grade_cache_key,
                        grade,
                        settings.JOANIE_ENROLLMENT_GRADE_CACHE_TTL,
                    )

        return grade

    def clean(self):
        """Clean instance fields and raise a ValidationError in case of issue."""
        # The related course run must be opened for enrollment
        if self.course_run.state["priority"] > courses_models.CourseState.ARCHIVED_OPEN:
            message = _(
                "You are not allowed to enroll to a course run not opened for enrollment."
            )
            raise ValidationError({"__all__": [message]})

        # The user should not be enrolled in another opened course run of the same course.
        if (
            self.created_on is None
            and self.user.enrollments.filter(
                course_run__course=self.course_run.course,
                course_run__end__gte=timezone.now(),
                is_active=True,
            ).exists()
        ):
            message = _(
                "You are already enrolled to an opened course run "
                f'for the course "{self.course_run.course.title}".'
            )
            raise ValidationError({"user": [message]})

        # Forbid creating a free enrollment if the related course run is not listed and
        # if the course relies on a product and the owner doesn't purchase it.
        if not self.course_run.is_listed:
            if self.course_run.course.targeted_by_products.exists():
                validated_user_orders = [
                    order
                    for order in Order.objects.filter(
                        (
                            models.Q(
                                course_relations__course_runs__isnull=True,
                                target_courses__course_runs=self.course_run,
                            )
                            | models.Q(course_relations__course_runs=self.course_run)
                        ),
                        is_canceled=False,
                        owner=self.user,
                    )
                    if order.state == enums.ORDER_STATE_VALIDATED
                ]
                if len(validated_user_orders) == 0:
                    message = _(
                        f'Course run "{self.course_run.resource_link:s}" '
                        "requires a valid order to enroll."
                    )
                    raise ValidationError({"__all__": [message]})
            else:
                message = _("You are not allowed to enroll to a course run not listed.")
                raise ValidationError({"__all__": [message]})

        return super().clean()

    def set(self):
        """Try setting the state to the LMS. Saving is left to the caller."""
        # Now we can enroll user to LMS course run
        link = self.course_run.resource_link
        lms = LMSHandler.select_lms(link)

        if lms is None:
            # If no lms found we set enrollment and order to failure state
            # this issue could be due to a bad setting or a bad resource_link filled,
            # so we need to log this error to fix it quickly to joanie side
            logger.error('No LMS configuration found for course run: "%s".', link)
            self.state = enums.ENROLLMENT_STATE_FAILED
        elif (
            not self.created_on
            or Enrollment.objects.only("is_active").get(pk=self.pk).is_active
            != self.is_active
        ):
            # Try to enroll user to lms course run and update joanie's enrollment state
            try:
                lms.set_enrollment(self.user.username, link, self.is_active)
            except EnrollmentError:
                logger.error('Enrollment failed for course run "%s".', link)
                self.state = enums.ENROLLMENT_STATE_FAILED
            else:
                self.state = enums.ENROLLMENT_STATE_SET

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        self.set()
        models.Model.save(self, *args, **kwargs)
