"""
Declare and configure the models for the products part
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
    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    type = models.CharField(
        _("type"), choices=enums.PRODUCT_TYPE_CHOICES, max_length=50
    )
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255),
        call_to_action=models.CharField(_("call to action"), max_length=255),
    )
    course = models.ForeignKey(
        courses_models.Course,
        verbose_name=_("course"),
        related_name="products",
        on_delete=models.PROTECT,
    )
    course_runs = models.ManyToManyField(
        courses_models.CourseRun, verbose_name=_("course runs")
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

    def get_course_runs_available_for_each_position(self):
        """Get all course runs available for the product grouped by position"""
        course_runs_available = {}
        for course_run, position in [
            (course_run, course_run.positions.get(product=self).position)
            for course_run in self.course_runs.all()
        ]:
            course_runs_available.setdefault(position, set()).add(course_run)
        return course_runs_available

    def set_order(self, user, resource_links):
        """
        Create a new order and enrollments to course runs selected for a user.
        Call lms to enroll user to each course run.

        Args:
            user: User, owner of the order
            resource_links: list, resource_links of all course runs selected for the course product

        Returns:
            Order

        Raises:
            OrderAlreadyExists: if an valid order already exists for this product
        """
        # For a user, no more than one active order for a product can exist.
        # Check if an order already exists for this product.
        # If an order already exists, we can create another one if only order state is 'canceled'
        # If user changes his/her mind about course runs selected,
        # the order has to be set to state 'canceled' and another order has to be created
        if (
            Order.objects.filter(product=self, owner=user)
            .exclude(state__in=[enums.ORDER_STATE_CANCELED])
            .exists()
        ):
            raise exceptions.OrderAlreadyExists("Order already exists")

        # Check consistently of resource_links set
        # First prevent unnecessary duplicated enrollments
        resource_links = set(resource_links)
        # Get all course runs available for the product grouped by position
        product_course_runs_available = (
            self.get_course_runs_available_for_each_position()
        )
        # User has to select exactly one course run per necessary step defined (one per position)
        if len(resource_links) != len(product_course_runs_available):
            raise exceptions.InvalidCourseRuns(
                f"{len(product_course_runs_available)} course runs have to be selected, "
                f"{len(resource_links)} given"
            )
        # Make sure user chooses one of course runs for each necessary step (position)
        # first extract valid course runs selected by user for each necessary step
        valid_course_runs_selected = {}
        for resource_link in resource_links:
            # Course run has to be available for the product
            # Raise ObjectDoesNotExist if it's not a resource_link of one of course runs
            # available for the product
            course_run = self.course_runs.get(resource_link=resource_link)
            for position, course_runs in product_course_runs_available.items():
                if course_run in list(course_runs):
                    valid_course_runs_selected[position] = course_run
        # We need exactly one course run selected for each necessary step
        if len(valid_course_runs_selected) != len(product_course_runs_available):
            raise exceptions.InvalidCourseRuns(
                f"{len(product_course_runs_available)} course runs have to be selected, "
                f"{len(valid_course_runs_selected)} given"
            )

        # So now everything is fine, we can create an order
        order = Order.objects.create(product=self, owner=user)
        for position in sorted(valid_course_runs_selected.keys()):
            # associate each course run selected to the order
            course_run = valid_course_runs_selected[position]
            order.course_runs.add(course_run)
            # then create enrollment for each course run
            enrollment = Enrollment.objects.create(course_run=course_run, order=order)
            # now we can enroll user to LMS course run
            lms = LMSHandler.select_lms(course_run.resource_link)
            # now try to enroll user to lms course run and change joanie enrollment
            # state to 'in_progress'
            try:
                lms_enrollment = lms.set_enrollment(
                    user.username, course_run.resource_link
                )
                if lms_enrollment["is_active"]:
                    enrollment.state = enums.ENROLLMENT_STATE_IN_PROGRESS
                    enrollment.save()
            except (TypeError, AttributeError):
                # if no lms found we set enrollment and order to failure state
                # this issue could be due to a bad setting or a bad resource_link filled,
                # so we need to log this error to fix it quickly to joanie side
                if not lms:
                    logger.error(
                        "No LMS configuration found for resource link: %s",
                        course_run.resource_link,
                    )
                order.state = enums.ORDER_STATE_FAILED
                order.save()
                enrollment.state = enums.ENROLLMENT_STATE_FAILED
                enrollment.save()
        return order


class ProductCourseRunPosition(models.Model):
    """
    ProductCourseRunPosition model allows to define order of each course runs to follow
    for a product.
    Some course runs could have the same position for a product (various sessions for example).
    Validation of only one of them will be enough to pass to the next course run or certification.
    """

    product = models.ForeignKey(
        Product,
        verbose_name=_("product"),
        related_name="course_runs_positions",
        on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField(_("position in product"))
    course_run = models.ForeignKey(
        courses_models.CourseRun,
        verbose_name=_("course run"),
        related_name="positions",
        on_delete=models.RESTRICT,
    )

    class Meta:
        db_table = "joanie_product_course_run_position"
        verbose_name = _("Position of course runs in products")
        verbose_name_plural = _("Positions of course runs in products")
        unique_together = ("product", "course_run", "position")

    def __str__(self):
        return f"{self.product}: {self.position}/ {self.course_run}]"


class Order(models.Model):
    """
    Order model represents and records details user's order (for free or not) to a course product
    All course runs to enroll selected are defined here.
    """

    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    product = models.ForeignKey(
        Product,
        verbose_name=_("product"),
        related_name="orders",
        on_delete=models.RESTRICT,
    )
    course_runs = models.ManyToManyField(
        courses_models.CourseRun, verbose_name=_("course runs")
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
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"


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
        on_delete=models.RESTRICT,
    )
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
