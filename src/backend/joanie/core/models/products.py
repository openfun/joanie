"""
Declare and configure the models for the productorder_s part
"""
import logging
import uuid
from decimal import Decimal as D

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from babel.numbers import get_currency_symbol
from djmoney.models.fields import MoneyField
from djmoney.models.validators import MinMoneyValidator
from marion.models import DocumentRequest
from parler import models as parler_models

from joanie.core.exceptions import EnrollmentError
from joanie.lms_handler import LMSHandler

from .. import enums, utils
from . import accounts as customers_models
from . import certifications as certifications_models
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
            and self.type not in PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ):
            raise ValidationError(
                _(
                    f"Certificate definition is only allowed for product kinds: "
                    f"{', '.join(PRODUCT_TYPE_CERTIFICATE_ALLOWED)}"
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
    state = models.CharField(
        _("type"),
        choices=enums.ORDER_STATE_CHOICES,
        default=enums.ORDER_STATE_PENDING,
        max_length=50,
    )
    invoice_ref = models.CharField(_("invoice reference"), blank=True, max_length=40)

    class Meta:
        db_table = "joanie_order"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "owner", "product"],
                condition=~models.Q(state=enums.ORDER_STATE_CANCELED),
                name="unique_owner_product_not_canceled",
            )
        ]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order {self.product} for user {self.owner}"

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
            for relation in ProductCourseRelation.objects.filter(product=self.product):
                OrderCourseRelation.objects.create(
                    order=self, course=relation.course, position=relation.position
                )

    def generate_invoice(self):
        """Generate a pdf invoice for an order"""

        vat = D(settings.JOANIE_VAT)
        net_amount = self.product.price.amount  # pylint: disable=no-member
        vat_amount = net_amount * vat / 100
        # create a unique reference for invoice
        reference = (
            f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
            "-"
            f"{str(self.uid).split('-', maxsplit=1)[0]}"
        )
        currency = get_currency_symbol(
            self.product.price.currency.code  # pylint: disable=no-member
        )

        # pylint: disable = fixme
        # TODO: It is currently weird to use the main address to generate the invoice.
        # Instead, we should use the billing address provided during the payment.
        try:
            main_address = self.owner.addresses.get(is_main=True)
        except ObjectDoesNotExist as error:
            self.state = enums.ORDER_STATE_FAILED
            self.save()
            raise ValueError(
                _("A billing address is missing, invoice cannot be generated.")
            ) from error

        context = {
            "metadata": {
                "reference": reference,
                "type": "invoice",
                "issued_on": timezone.now(),
            },
            "order": {
                "customer": {
                    "name": main_address.full_name,
                    "address": main_address.full_address,
                },
                "seller": {
                    "address": settings.JOANIE_INVOICE_SELLER_ADDRESS,
                },
                "product": {
                    "name": self.product.title,  # pylint: disable=no-member
                    "description": self.product.description,  # pylint: disable=no-member
                },
                "amount": {
                    "subtotal": net_amount,
                    "total": (net_amount + vat_amount),
                    "vat_amount": vat_amount,
                    "vat": vat,
                    "currency": currency,
                },
                "company": settings.JOANIE_INVOICE_COMPANY_CONTEXT,
            },
        }
        invoice = DocumentRequest.objects.create(
            issuer=settings.MARION_INVOICE_DOCUMENT_ISSUER,
            context_query=context,
        )
        # save reference to invoice_ref field
        self.invoice_ref = reference
        self.save()
        return invoice

    def generate_certificate(self):
        """Generate a pdf certificate for the order's owner"""
        organization = self.course.organization
        context_query = {
            "student": {
                "name": self.owner.get_full_name(),
            },
            "course": {
                "name": self.product.title,  # pylint: disable=no-member
                "organization": {
                    "name": organization.title,
                    "representative": organization.representative,
                    "signature": utils.image_to_base64(organization.signature),
                    "logo": utils.image_to_base64(organization.logo),
                },
            },
        }
        document_request = DocumentRequest.objects.create(
            issuer=self.product.certificate_definition.template,  # pylint: disable=no-member
            context_query=context_query,
        )
        certificate, _ = certifications_models.Certificate.objects.update_or_create(
            order=self,
            defaults={"attachment": document_request.get_document_path().name},
        )
        return certificate


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

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
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

    def clean(self):
        """Clean instance fields and raise a ValidationError in case of issue."""
        if self.order:
            # The user of the enrollment should be the owner of the order
            if self.order.owner != self.user:
                message = _(
                    f"You are not allowed to enroll on order {self.order.uid!s}."
                )
                raise ValidationError({"user": [message]})

            # The course run targeted by the enrollment should also be targeted by the order
            if not self.order.target_courses.filter(
                course_runs=self.course_run
            ).exists():
                message = _(
                    f'This order does not contain course run "{self.course_run.resource_link:s}".'
                )
                raise ValidationError({"__all__": [message]})

        if self.course_run.course.targeted_by_products.exists():
            # Forbid creating a free enrollment if an order exists for this course and
            # the owner has no pending order on it.
            if not self.order or not (
                self.order.state == enums.ORDER_STATE_VALIDATED
                and self.order.target_courses.filter(
                    course_runs=self.course_run
                ).exists()
            ):
                message = _(
                    f'Course run "{self.course_run.resource_link:s}" '
                    "requires a valid order to enroll."
                )
                raise ValidationError({"__all__": [message]})

            # Forbid enrolling to 2 course runs related to the same course for a given order
            check_enrollments_query = self.order.enrollments.filter(
                course_run__course=self.course_run.course_id, is_active=True
            )
            if self.pk:
                check_enrollments_query = check_enrollments_query.exclude(pk=self.pk)
            if check_enrollments_query.exists():
                message = _(
                    f'User "{self.user.username:s}" is already enrolled '
                    "to this course for this order."
                )
                raise ValidationError({"order": [message]})

        return super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        self.set()
        super().save(*args, **kwargs)

    def state_fail(self, message):
        """
        Mark the enrollment and the eventual order to a failed state and log the error.
        Saving is left to the caller.
        """
        logger.error(message)

        if self.order:
            self.order.state = enums.ORDER_STATE_FAILED
            self.order.save()

        self.state = enums.ENROLLMENT_STATE_FAILED

    def set(self):
        """Try setting the state to the LMS. Saving is left to the caller."""
        # Now we can enroll user to LMS course run
        link = self.course_run.resource_link
        lms = LMSHandler.select_lms(link)

        if lms is None:
            # If no lms found we set enrollment and order to failure state
            # this issue could be due to a bad setting or a bad resource_link filled,
            # so we need to log this error to fix it quickly to joanie side
            link = self.course_run.resource_link
            self.state_fail(f'No LMS configuration found for course run: "{link:s}".')

        elif (
            not self.pk
            or Enrollment.objects.only("is_active").get(pk=self.pk).is_active
            != self.is_active
        ):
            # Try to enroll user to lms course run and update joanie's enrollment state
            try:
                lms.set_enrollment(self.user.username, link, self.is_active)
            except EnrollmentError:
                self.state_fail(f'Enrollment failed for course run "{link:s}".')
            else:
                self.state = enums.ENROLLMENT_STATE_SET
