"""
Declare and configure the models for the productorder_s part
"""
import hashlib
import hmac
import itertools
import json
import logging
from decimal import Decimal as D

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

import requests
from djmoney.models.fields import MoneyField
from djmoney.models.validators import MinMoneyValidator
from parler import models as parler_models
from rest_framework.reverse import reverse
from urllib3.util import Retry

from joanie.core import enums
from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.core.models.certifications import Certificate
from joanie.lms_handler import LMSHandler

from . import accounts as customers_models
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
    organizations = models.ManyToManyField(
        to=courses_models.Organization,
        related_name="products",
        verbose_name=_("organizations"),
    )
    target_courses = models.ManyToManyField(
        to=courses_models.Course,
        related_name="targeted_by_products",
        through="ProductTargetCourseRelation",
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
              field on the ProductTargetCourseRelation model)

            - only the course runs specified on the product/course relation for target
              courses on which a list of eligible course runs was specified on the
              product/course relation.

        """
        course_relations_with_course_runs = self.course_relations.filter(
            course_runs__isnull=False
        ).only("pk")

        return courses_models.CourseRun.objects.filter(
            models.Q(product_relations__in=course_relations_with_course_runs)
            | models.Q(
                course__in=self.target_courses.exclude(
                    product_relations__in=course_relations_with_course_runs
                )
            )
        )

    def get_equivalent_course_run_data(self):
        """
        Return data for the virtual course run equivalent to this product when, taking
        into account all course runs targeted by the product if any.

        The dates (start, end, enrollment start and enrollment end) and languages of this
        equivalent course run are calculated based on the course runs of each course targeted
        by this product.

        If a product has no target courses or no related course runs, it will still return
        an equivalent course run with null dates and hidden visibility.
        """
        site = Site.objects.get_current()
        aggregate = self.target_course_runs.aggregate(
            models.Min("start"),
            models.Max("end"),
            models.Max("enrollment_start"),
            models.Min("enrollment_end"),
        )
        resource_path = reverse("products-detail", kwargs={"id": self.id})
        return {
            "resource_link": f"https://{site.domain:s}{resource_path:s}",
            "catalog_visibility": enums.COURSE_AND_SEARCH
            if any(aggregate.values())
            else enums.HIDDEN,
            "languages": self.equivalent_course_run_languages,
            # Get dates from aggregate
            **{
                key.split("__")[0]: value.isoformat() if value else None
                for key, value in aggregate.items()
            },
        }

    @property
    def equivalent_course_run_languages(self):
        """Return a list of distinct languages available in alphabetical order."""
        languages = self.target_course_runs.values_list(
            "languages", flat=True
        ).distinct()
        # Go through a set for uniqueness of each language then return an ordered list
        return sorted(list(set(itertools.chain.from_iterable(languages))))

    @staticmethod
    def synchronize_products(products, visibility=None):
        """
        Synchronize a product's related course runs by calling remote web hooks.

        visibility: [CATALOG_VISIBILITY_CHOICES]:
            If not None, force visibility for the synchronized products. Useful when
            synchronizing a product that does not have anymore course runs and should
            therefore be hidden.
        """
        if not settings.COURSE_WEB_HOOKS:
            return

        equivalent_course_runs = []
        for product in products:
            if course_run_dict := product.get_equivalent_course_run_data():
                if visibility:
                    course_run_dict["catalog_visibility"] = visibility
                for course in product.courses.only("code").iterator():
                    equivalent_course_runs.append(
                        {**course_run_dict, "course": course.code}
                    )

        if not equivalent_course_runs:
            return

        json_equivalent_course_runs = json.dumps(equivalent_course_runs).encode("utf-8")
        for webhook in settings.COURSE_WEB_HOOKS:
            signature = hmac.new(
                str(webhook["secret"]).encode("utf-8"),
                msg=json_equivalent_course_runs,
                digestmod=hashlib.sha256,
            ).hexdigest()

            response = session.post(
                webhook["url"],
                json=equivalent_course_runs,
                headers={"Authorization": f"SIG-HMAC-SHA256 {signature:s}"},
                verify=bool(webhook.get("verify", True)),
                timeout=3,
            )

            extra = {
                "sent": json_equivalent_course_runs,
                "response": response.content,
            }
            # pylint: disable=no-member
            if response.status_code == requests.codes.ok:
                logger.info(
                    "Synchronisation succeeded with %s",
                    webhook["url"],
                    extra=extra,
                )
            else:
                logger.error(
                    "Synchronisation failed with %s",
                    webhook["url"],
                    extra=extra,
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


class ProductTargetCourseRelation(BaseModel):
    """
    ProductTargetCourseRelation model allows to define position of each courses to follow
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
    # allow restricting what course runs are proposed
    # for a given course when a product is bought.
    course_runs = models.ManyToManyField(
        courses_models.CourseRun,
        related_name="product_relations",
        verbose_name=_("course runs"),
        blank=True,
    )
    position = models.PositiveSmallIntegerField(_("position in product"))
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
        the developper to handle these cases correctly.
        """
        super().delete(using, keep_parents)
        self.synchronize_with_webhooks()

    def synchronize_with_webhooks(self):
        """Trigger webhook calls to keep remote apps synchronized."""
        Product.synchronize_products([self.product])


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
        through="OrderTargetCourseRelation",
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
        if (
            not self.created_on
            and self.course_id
            and self.product_id
            and self.organization_id
            and not Product.objects.filter(
                courses=self.course_id, organizations=self.organization_id
            ).exists()
        ):
            # pylint: disable=no-member
            message = _(
                f'The course "{self.course.title}" and the organization '
                f'"{self.organization.title}" should be linked to the product '
                f'"{self.product.title}".'
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
                    was_created_by_order=True,
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
            if self.was_created_by_order is False:
                # --> *1
                message = _(
                    "You cannot enroll to a non-listed course run out of the scope of an order."
                )
                raise ValidationError({"was_created_by_order": [message]})
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
