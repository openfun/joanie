"""
Declare and configure the models for the productorder_s part
"""
import logging
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models

from joanie.lms_handler import LMSHandler

from .. import enums, exceptions
from . import accounts as customers_models
from . import courses as courses_models

logger = logging.getLogger(__name__)
PRODUCT_TYPE_CERTIFICATE_ALLOWED = [
    enums.PRODUCT_TYPE_CERTIFICATE,
    enums.PRODUCT_TYPE_CREDENTIAL,
]


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
        call_to_action=models.CharField(_("call to action"), max_length=255),
    )
    course = models.ForeignKey(
        courses_models.Course,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("course"),
    )
    target_courses = models.ManyToManyField(
        courses_models.Course,
        related_name="included_in_products",
        through="ProductCourseRelation",
        verbose_name=_("target courses"),
    )
    target_course_runs = models.ManyToManyField(
        courses_models.CourseRun,
        related_name="included_in_products",
        verbose_name=_("course runs"),
    )
    price = models.CharField(
        _(f"price ({getattr(settings, 'CURRENCY')[1]})"),
        blank=True,
        max_length=100,
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
        ordering = ("-pk",)

    def __str__(self):
        return (
            f"[{self.type.upper()}] {self.safe_translation_getter('title', any_language=True)}"
            f" for {self.course} - {self.price}{getattr(settings, 'CURRENCY')[1]}"
        )

    def clean(self):
        # Allow certificate definition only for product with type credential or certificate
        if (
            self.certificate_definition
            and self.type not in PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ):
            raise ValidationError(
                _(
                    f"Certificate definition is only allowed for product kinds: "
                    f"{', '.join(PRODUCT_TYPE_CERTIFICATE_ALLOWED)}"
                )
            )
        super().clean()

    def set_order(self, user):
        """
        Create a new order for a user.

        Args:
            user: User, owner of the order

        Returns:
            Order

        Raises:
            OrderAlreadyExists: if the user already has a valid order for this product
        """
        # For a user, no more than one active order for a product can exist.
        # Check if an order already exists for this product.
        # If an order already exists, we can create another one if only order state is 'canceled'
        # If user changes his/her mind, the order has to be set to state 'canceled' and another
        # order has to be created
        if (
            Order.objects.filter(product=self, owner=user)
            .exclude(state__in=[enums.ORDER_STATE_CANCELED])
            .exists()
        ):
            raise exceptions.OrderAlreadyExists("Order already exists")

        # Everything is fine, we can create an order
        order = Order.objects.create(product=self, owner=user)
        return order


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

    class Meta:
        db_table = "joanie_product_course_relation"
        ordering = ("position", "course")
        unique_together = ("product", "course")
        verbose_name = _("Course relation to a product with a position")
        verbose_name_plural = _("Courses relations to products with a position")

    def __str__(self):
        return f"{self.product}: {self.position}/ {self.course}]"


class Order(models.Model):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    title = (models.CharField(_("title"), max_length=255),)
    product = models.ForeignKey(
        Product,
        verbose_name=_("product"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    courses = models.ManyToManyField(
        courses_models.Course,
        related_name="orders",
        through="OrderCourseRelation",
        verbose_name=_("courses"),
    )
    price = models.CharField(
        _(f"price ({getattr(settings, 'CURRENCY')[1]})"),
        blank=True,
        max_length=100,
    )
    owner = models.ForeignKey(
        customers_models.User,
        verbose_name=_("owner"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    created_on = models.DateTimeField(_("created on"), default=timezone.now)
    updated_on = models.DateTimeField(_("updated on"), auto_now=True)
    state = models.CharField(
        _("type"),
        choices=enums.ORDER_STATE_CHOICES,
        default=enums.ORDER_STATE_PENDING,
        max_length=50,
    )

    class Meta:
        db_table = "joanie_order"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "product"],
                condition=~models.Q(state=enums.ORDER_STATE_CANCELED),
                name="unique_owner_product_not_canceled",
            )
        ]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

    def set_enrollments(self):
        """"Create an enrollment for each course run related to the order."""
        enrollments = []
        for course_run in self.course_runs.all():
            enrollments.append(
                Enrollment.objects.create(
                    course_run=course_run, order=self, owner=self.owner
                )
            )
        for enrollment in enrollments:
            enrollment.set()


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

    class Meta:
        db_table = "joanie_order_course_relation"
        ordering = ("position", "course")
        unique_together = ("order", "course")
        verbose_name = _("Course relation to an order with a position")
        verbose_name_plural = _("Courses relations to orders with a position")

    def __str__(self):
        return f"{self.order}: {self.position}/ {self.course}]"


class Enrollment(models.Model):
    """
    Enrollment model represents and records lms enrollment state for course run
    as part of an order
    """

    course_run = models.ForeignKey(
        courses_models.CourseRun,
        verbose_name=_("course run"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    order = models.ForeignKey(
        Order,
        verbose_name=_("order"),
        related_name="enrollments",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
    )
    owner = models.ForeignKey(
        customers_models.User,
        verbose_name=_("owner"),
        related_name="enrollments",
        on_delete=models.RESTRICT,
    )
    created_on = models.DateTimeField(_("created on"), default=timezone.now)
    updated_on = models.DateTimeField(_("updated on"), auto_now=True)
    # lms enrollment to course run state will be updated with elastic
    state = models.CharField(
        _("state"),
        choices=enums.ENROLLMENT_STATE_CHOICES,
        default=enums.ENROLLMENT_STATE_PENDING,
        max_length=50,
    )

    class Meta:
        db_table = "joanie_enrollment"
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def __str__(self):
        return f"[{self.state}] {self.course_run} for {self.order.owner}"

    def set(self):
        # now we can enroll user to LMS course run
        lms = LMSHandler.select_lms(self.course_run.resource_link)
        # now try to enroll user to lms course run and change joanie enrollment
        # state to 'in_progress'
        try:
            lms_enrollment = lms.set_enrollment(
                self.owner.username, self.course_run.resource_link
            )
            if lms_enrollment["is_active"]:
                self.state = enums.ENROLLMENT_STATE_IN_PROGRESS
                self.save()
        except (TypeError, AttributeError):
            # if no lms found we set enrollment and order to failure state
            # this issue could be due to a bad setting or a bad resource_link filled,
            # so we need to log this error to fix it quickly to joanie side
            if not lms:
                logger.error(
                    "No LMS configuration found for resource link: %s",
                    self.course_run.resource_link,
                )
            self.order.state = enums.ORDER_STATE_FAILED
            self.order.save()
            self.state = enums.ENROLLMENT_STATE_FAILED
            self.save()
