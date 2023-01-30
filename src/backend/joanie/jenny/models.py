"""
Models for the administration, legal and consulting&projects teams
"""
import hashlib
from os.path import splitext

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

from django_fsm import FSMField

from ..core.models import BaseModel, Organization


class CourseSubmission(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Manager"),
        on_delete=models.PROTECT,
        related_name="pre_courses",
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("Organization"),
        help_text=_("the organization in which the course will take place"),
        on_delete=models.PROTECT,
        related_name="pre_courses",
    )
    title = models.CharField(
        verbose_name=_("Title"), max_length=255, null=False, blank=False
    )
    date = models.DateField(verbose_name=_("Course start date"))
    state = FSMField(default='new')
    # new -> org_approval_sent
    # org_approval_sent -> org_approval_received
    # org_approval_received -> final_validation_pending
    # new -> quote_sent
    # quote_sent -> order_received
    # order_received -> final_validation_pending
    # final_validation_pending -> accepted
    # new -> refused
    # org_approval_sent -> refused
    # org_approval_received -> refused
    # final_validation_pending -> refused
    # quote_sent -> refused
    # order_received -> refused


class CourseSubmissionProduct(BaseModel):
    couse_submission = models.ForeignKey(CourseSubmission, verbose_name=_('Course submission'), on_delete=models.PROTECT)
    product = models.ForeignKey('Product', verbose_name=_('Product'), on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(verbose_name=_('quantity'), null=True, default=None)


class Pricing(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    # MEMBERSHIP_LEVEL_1
    # MEMBERSHIP_LEVEL_2
    # MEMBERSHIP_LEVEL_3
    # PARTNER
    # PUBLIC_WO_PERSON

    def __str__(self):
        return self.name


class Product(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    code = models.CharField(max_length=255, verbose_name=_("Code"))
    submission_enabled = models.BooleanField(default=False, verbose_name=_('Enabled in course submission wizard'))

    def __str__(self):
        return self.name
    # MEMBERSHIP_LEVEL_1
    # MEMBERSHIP_LEVEL_2
    # MEMBERSHIP_LEVEL_3
    # MOOC_STANDARD
    # MOOC_SELF_PACED
    # MOOC_OPEN_ARCHIVE
    # SPOCA_INSTANCIATION
    # SPOCA_LEARNERS
    # SPOCC_FUN
    # SPOCC_ORG
    # DOUBLE_DISPLAY
    # CERT


class ProductPrice(BaseModel):
    pricing = models.ForeignKey(
        Pricing,
        verbose_name=_("Pricing"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_('Product'),
        on_delete=models.PROTECT,
    )
    year = models.PositiveSmallIntegerField(
        verbose_name=_("Year"), validators=[MinValueValidator(2022)]
    )

    FLAT = 'flat'
    RANGE = 'range'
    PERCENT = 'percent'
    PACKLINES = 'packlines'
    PRICE_TYPE_CHOICES = [
        (FLAT, _('flat')),
        (RANGE, _('range')),
        (PERCENT, _('percent')),
        (PACKLINES, _('packlines')),
    
    ]
    price_type = models.CharField(
        verbose_name=_("Price type"),
        max_length=max([len(e[0]) for e in PRICE_TYPE_CHOICES]),
        choices=PRICE_TYPE_CHOICES,
    )
    price_flat = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price"),
        null=True,
        default=None,
        blank=True,
    )

    price_percent = models.PositiveSmallIntegerField(
        verbose_name=_("Percent"), validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        default=None,
        blank=True,
    )
    price_percent_minimum = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price percent minimum"),
        null=True,
        default=None,
        blank=True,
    )

    YEAR = "year"
    COURSE = 'course'
    LEARNER = 'learner'
    REVENUE = 'revenue'
    UNIT_CHOICES = [
        (YEAR, _('Year')),
        (COURSE, _('Course')),
        (LEARNER, _('Learner')),
        (REVENUE, _('Revenue')),
    ]
    unit = models.CharField(
        verbose_name=_("Unit"),
        max_length=max([len(e[0]) for e in UNIT_CHOICES]),
        choices=UNIT_CHOICES,
    )
    
    def __str__(self):
        return f"{self.pricing} {self.product}"


class ProductPriceRange(BaseModel):
    product_price = models.ForeignKey(
        ProductPrice,
        verbose_name=_("Product price"),
        on_delete=models.PROTECT,
    )
    range_start = models.PositiveSmallIntegerField(
        verbose_name=_("Range start"), validators=[MinValueValidator(0)]
    )
    range_end = models.PositiveSmallIntegerField(
        verbose_name=_("Range end"),
        validators=[MinValueValidator(1)],
        null=True,
        default=None,
        blank=True,
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Unit price")
    )
    minimum = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Range minimum price")
    )
    

class ProductPricePackLine(BaseModel):
    product_price = models.ForeignKey(
        ProductPrice,
        verbose_name=_('Product price'),
        on_delete=models.CASCADE,
        related_name="pack_lines",
    )
    FLAT = 'flat'
    UNLIMITED = 'unlimited'
    QUANTITY_TYPE_CHOICES = [
        (FLAT, _('Flat')),
        (UNLIMITED, _('Unlimited')),
    ]
    quantity_type = models.CharField(
        verbose_name=_("Quantity type"),
        max_length=max([len(e[0]) for e in QUANTITY_TYPE_CHOICES]),
        choices=QUANTITY_TYPE_CHOICES,
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name=_("Quantity"),
        null=True,
        default=None,
        blank=True,
    )
    included_products = models.ManyToManyField(Product)


def contract_upload_to(instance, filename):
    _, ext = splitext(filename)
    ctx = hashlib.sha256()
    ctx.update(instance.file.read())
    file_hash = ctx.hexdigest()
    return "organization/{instance.organization.id}/contracts/{file_hash}.{file_ext}"


class Contract(BaseModel):
    start = models.DateField(verbose_name=_("start of the contract"))
    end = models.DateField(
        verbose_name=_("end of the contract"), null=True, default=None, blank=True
    )
    file = models.FileField(
        verbose_name=_("file of the signed contract"), upload_to=contract_upload_to
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("organization"),
        help_text=_("the organization signing the contract"),
        on_delete=models.PROTECT,
    )
    pricing = models.ForeignKey(
        Pricing,
        verbose_name=_("Pricing"),
        help_text=_("the pricing to apply with this contract"),
        on_delete=models.PROTECT,
    )


class Transaction(BaseModel):
    invoice = models.ForeignKey(
        "Invoice",
        verbose_name=_("Invoice"),
        on_delete=models.CASCADE,
        help_text=_("source of credit"),
    )
    course_submission = models.ForeignKey(
        CourseSubmission,
        verbose_name=_("Course submission"),
        help_text=_("source of debit"),
        on_delete=models.PROTECT,
    )
    products = models.ManyToManyField(Product)
    debit = models.PositiveIntegerField(
        verbose_name=_("Debit"),
    )
    credit = models.PositiveIntegerField(verbose_name=_("Credit"))
    unlimited_credit = models.BooleanField(null=True, default=None, verbose_name=_('Unlimited credit'))


class Quote(BaseModel):
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    external_ref = models.CharField(max_length=255, verbose_name=_("External Reference"))
    state = FSMField(default='to_send')
    # to_send -> sent
    # sent -> order_received
    # sent -> cancelled
    # to_send -> cancelled


class QuoteLine(BaseModel):
    quote = models.ForeignKey(
        Quote,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_('Product'),
        on_delete=models.PROTECT,
    )
    label = models.TextField(verbose_name=_("Label"))
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Unit price")
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Quantity")
    )


class Invoice(BaseModel):
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    external_ref = models.CharField(max_length=255, verbose_name=_("External Reference"))
    state = FSMField(default='to_send')
    # to_send -> sent
    # to_send -> cancelled


class InvoiceLine(BaseModel):
    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_('Product'),
        on_delete=models.PROTECT,
    )
    label = models.TextField(verbose_name=_("Label"))
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Unit price")
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Quantity")
    )
