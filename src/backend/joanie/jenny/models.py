"""
Models for the administration, legal and consulting&projects teams
"""
import hashlib
from os.path import splitext

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

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
    start_date = models.DateField(verbose_name=_("Course start date"))
    double_display = models.BooleanField(
        default=False,
        verbose_name=_("Double display"),
    )

    MOOC = "MOOC"
    SPOCA = "SPOCA"
    SPOCC = "SPOCC"
    KIND_CHOICES = [
        (MOOC, _("MOOC")),
        (SPOCA, _("Academic SPOC")),
        (SPOCC, _("Corporate SPOC")),
    ]
    kind = models.CharField(
        verbose_name=_("Kind"),
        max_length=max([len(e[0]) for e in KIND_CHOICES]),
        choices=KIND_CHOICES,
        default=None,
        null=True,
    )
    STANDARD = "STANDARD"
    OPEN_ARCHIVE = "OPEN_ARCHIVE"
    SELF_PACED = "SELF_PACED"

    MOOC_KIND_CHOICES = [
        (STANDARD, _("Standard")),
        (OPEN_ARCHIVE, _("Archivé ouvert")),
        (SELF_PACED, _("Self-paced")),
    ]
    mooc_kind = models.CharField(
        verbose_name=_("Mooc kind"),
        choices=MOOC_KIND_CHOICES,
        max_length=max([len(e[0]) for e in MOOC_KIND_CHOICES]),
        blank=True,
        default=STANDARD,
        null=True,
    )
    spoc_learner_quantity = models.PositiveIntegerField(
        verbose_name=_("Learner quantity"), null=True, blank=True
    )
    spocc_certificate = models.BooleanField(
        default=False,
        verbose_name=_("SPOC Corporate Certificate"),
    )


class Pricing(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    level = models.PositiveSmallIntegerField(
        verbose_name=_("Level"), null=True, blank=True
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price")
    )
    year = models.PositiveSmallIntegerField(
        verbose_name=_("Year"), validators=[MinValueValidator(2023)]
    )
    course_quantity = models.PositiveSmallIntegerField(
        verbose_name=_("Course quantity")
    )

    double_display_included = models.BooleanField(
        verbose_name=_("Double display included")
    )
    double_display_unit_price = models.PositiveSmallIntegerField(
        verbose_name=_("Double display unit price"), null=True, blank=True
    )
    course_over_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Out of package course unit price"),
    )
    course_archived_open_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Out of package archived open course unit price"),
    )
    campus_new_unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Campus new course unit price")
    )
    campus_learner_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Campus unit price by learner")
    )
    fpc_fun_percent = models.PositiveSmallIntegerField(
        verbose_name=_("FUN percentage on Continuous Professionnal Formation"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fpc_fun_mini = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("FPC minimum price")
    )
    fpc_certificate = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("FPC price by certificate")
    )


class PricingFPCbyOrg(BaseModel):
    pricing = models.ForeignKey(
        Pricing,
        verbose_name=_("Pricing"),
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
        max_digits=10, decimal_places=2, verbose_name=_("Price by learner")
    )
    minimum = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Range minimum price")
    )


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
    debit = models.PositiveIntegerField(
        verbose_name=_("Debit"),
    )
    credit = models.PositiveIntegerField(verbose_name=_("Credit"))
    contract = models.ForeignKey(
        Contract,
        verbose_name=_("contract"),
        on_delete=models.CASCADE,
        help_text=_("source of credit"),
    )
    course_submission = models.ForeignKey(
        CourseSubmission,
        verbose_name=_("precours"),
        help_text=_("source of debit"),
        on_delete=models.PROTECT,
    )


class Quote(BaseModel):
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    pep_number = models.CharField(max_length=255, verbose_name=_("Quote number in PEP"))


class QuoteLine(BaseModel):
    quote = models.ForeignKey(
        Quote,
        verbose_name=_("Organization"),
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
    pep_number = models.CharField(max_length=255, verbose_name=_("Quote number in PEP"))


class InvoiceLine(BaseModel):
    quote = models.ForeignKey(
        Invoice,
        verbose_name=_("Organization"),
        on_delete=models.PROTECT,
    )
    label = models.TextField(verbose_name=_("Label"))
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Unit price")
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Quantity")
    )
