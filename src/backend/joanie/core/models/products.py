"""
Declare and configure the models for the productorder_s part
"""
import logging
import uuid
from decimal import Decimal as D

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
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

logger = logging.getLogger(__name__)


class Product(parler_models.TranslatableModel):
    """
    Product model represents detailed description of product to purchase for a course.
    All course runs and certification available for a product are defined here.
    """

    # uid used by cms to get order and enrollment
    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
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
        ordering = ("pk",)

    def __str__(self):
        return (
            f"[{self.type.upper()}] {self.safe_translation_getter('title', any_language=True)} "
            f"{self.price}"
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


class ProductCourseRelation(models.Model):
    """
    ProductCourseRelation model allows to define position of each courses to follow
    for a product.
    """

    course = models.ForeignKey(
        courses_models.Course,
        verbose_name=_("course"),
        related_name="product_relations",
        on_delete=models.RESTRICT,
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_("product"),
        related_name="course_relations",
        on_delete=models.CASCADE,
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


class Order(models.Model):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    course = models.ForeignKey(
        courses_models.Course,
        verbose_name=_("course"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
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
        customers_models.User,
        verbose_name=_("owner"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    created_on = models.DateTimeField(
        _("created on"), default=timezone.now, editable=False
    )
    updated_on = models.DateTimeField(_("updated on"), auto_now=True, editable=False)
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

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

    @property
    def state(self):
        """
        Return order state.
        If order has been explicitly canceled, return canceled state.
        Then if order is free or has a related invoice, return validated state
        Otherwise return pending state.
        """
        if self.is_canceled is True:
            return enums.ORDER_STATE_CANCELED

        if (
            self.total.amount == 0  # pylint: disable=no-member
            or self.invoices.count() > 0
        ):
            return enums.ORDER_STATE_VALIDATED

        return enums.ORDER_STATE_PENDING

    @cached_property
    def main_invoice(self):
        """
        Return main order's invoice.
        It corresponds to the only invoice related to the order without parent.
        """
        try:
            return self.invoices.get(parent__isnull=True)
        except ObjectDoesNotExist:
            return None

    def clean(self):
        """Clean instance fields and raise a ValidationError in case of issue."""
        if (
            not self.pk
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

        if not self.pk:
            self.total = self.product.price

        return super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        is_new = not bool(self.pk)
        super().save(*args, **kwargs)

        if is_new:
            # - Generate order course relation
            for relation in ProductCourseRelation.objects.filter(product=self.product):
                OrderCourseRelation.objects.create(
                    order=self,
                    course=relation.course,
                    position=relation.position,
                    is_graded=relation.is_graded,
                )

            self.validate()

    @transaction.atomic
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
                    user=self.owner, course_run=course_run
                ).only("is_active", "orders")
            except Enrollment.DoesNotExist:
                self.enrollments.add(  # pylint: disable=no-member
                    Enrollment.objects.create(
                        course_run=course_run,
                        user=self.owner,
                        is_active=True,
                    )
                )
            else:
                if enrollment.is_active is False:
                    enrollment.is_active = True
                    enrollment.save()
                if self not in enrollment.orders:
                    self.enrollments.add(enrollment)  # pylint: disable=no-member

    def cancel(self):
        """
        Mark order instance as "canceled" then unroll user to all active
        course runs related to the order.
        """
        # Unroll user to all active enrollment related to the order
        enrollments = self.enrollments.filter(is_active=True)
        for enrollment in enrollments:
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
                        f"the order {self.uid} "
                        f"on {self.certificate.issued_on}."
                    )
                )
            )

        Certificate.objects.create(order=self)


class OrderCourseRelation(models.Model):
    """
    OrderCourseRelation model allows to define position of each courses to follow
    for an order.
    """

    course = models.ForeignKey(
        courses_models.Course,
        verbose_name=_("course"),
        related_name="order_relations",
        on_delete=models.RESTRICT,
    )
    order = models.ForeignKey(
        Order,
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


class Enrollment(models.Model):
    """
    Enrollment model represents and records lms enrollment state for course run
    as part of an order
    """

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    course_run = models.ForeignKey(
        courses_models.CourseRun,
        verbose_name=_("course run"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    orders = models.ManyToManyField(
        Order,
        verbose_name=_("orders"),
        related_name="enrollments",
        blank=True,
    )
    user = models.ForeignKey(
        customers_models.User,
        verbose_name=_("user"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    created_on = models.DateTimeField(_("created on"), default=timezone.now)
    updated_on = models.DateTimeField(_("updated on"), auto_now=True)
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
        return f"grade_{self.uid}"

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

        if self.course_run.course.targeted_by_products.exists():
            # Forbid creating a free enrollment if an order exists for this course and
            # the owner has no pending order on it.
            validated_user_orders = [
                order
                for order in Order.objects.filter(
                    is_canceled=False,
                    owner=self.user,
                    target_courses__course_runs=self.course_run,
                )
                if order.state == enums.ORDER_STATE_VALIDATED
            ]
            if len(validated_user_orders) == 0:
                message = _(
                    f'Course run "{self.course_run.resource_link:s}" '
                    "requires a valid order to enroll."
                )
                raise ValidationError({"__all__": [message]})

        return super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        self.set()
        super().save(*args, **kwargs)

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
            not self.pk
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


def on_enrollment_orders_linked(action, instance, pk_set, **kwargs):
    """Process some checks before link orders to an enrollment."""
    if action != "pre_add":
        return

    def is_order_owner(enrollment, order):
        """Check if the enrollment's user is the owner of the order"""
        if order.owner != enrollment.user:
            return False
        return True

    def does_enrollment_rely_on_order_target_course(enrollment, order):
        """
        Check if the course run targeted by the enrollment is also targeted by the order
        """
        if not order.target_courses.filter(course_runs=enrollment.course_run).exists():
            return False

        return True

    def check_enrollments(enrollment, order):
        check_enrollments_query = order.enrollments.filter(
            course_run__course=enrollment.course_run.course_id,
            is_active=True,
        ).exclude(pk=enrollment.pk)

        if check_enrollments_query.exists():
            return True

        return False

    if isinstance(instance, Order):
        enrollments = Enrollment.objects.filter(pk__in=pk_set)
        order_set = {instance.pk}
    else:
        enrollments = [instance]
        order_set = pk_set

    for enrollment in enrollments:
        for order in Order.objects.filter(pk__in=order_set):
            # - Enrollment should rely on a course targeted by the order
            if not does_enrollment_rely_on_order_target_course(enrollment, order):
                message = _(
                    f'This order does not contain course run "{enrollment.course_run.resource_link:s}".'  # noqa pylint: disable=line-too-long
                )
                raise ValidationError({"__all__": [message]})

            # - Order owner should be the enrollment user
            if not is_order_owner(enrollment, order):
                message = _(f"You are not allowed to enroll on order {order.uid!s}.")
                raise ValidationError({"user": [message]})

            # - Order should be validated
            if order.state != enums.ORDER_STATE_VALIDATED:
                message = _(
                    "You are not allowed to enroll on order which is not validated."
                )
                raise ValidationError({"user": [message]})

            # Forbid enrolling to 2 course runs related to the same course for a given order
            if check_enrollments(enrollment, order):
                message = _(
                    f'User "{enrollment.user.username:s}" is already enrolled '
                    "to this course for this order."
                )
                raise ValidationError({"orders": [message]})


m2m_changed.connect(on_enrollment_orders_linked, sender=Enrollment.orders.through)
