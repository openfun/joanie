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


class PreCourse(BaseModel):
    STANDARD = "STANDARD"
    MOOC_FOLIO = "MOOC_FOLIO"
    OPEN_ARCHIVE = "OPEN_ARCHIVE"
    SELF_PACED = "SELF_PACED"
    THEME_PROJECT_INSTANCE = "THEME_PROJECT_INSTANCE"

    STATUSES = [
        (STANDARD, _("Standard")),
        (MOOC_FOLIO, _("MOOC folio")),
        (OPEN_ARCHIVE, _("Archivé ouvert")),
        (SELF_PACED, _("Self-paced")),
        (THEME_PROJECT_INSTANCE, _("Instance projet-theme")),
    ]
    submission_date = models.DateField(
        verbose_name=_("Submission date"), null=False, blank=False
    )
    title = models.CharField(
        verbose_name=_("Title"), max_length=255, null=False, blank=False
    )
    status = models.CharField(
        verbose_name=_("Status"),
        choices=STATUSES,
        max_length=max([len(e[0]) for e in STATUSES]),
        blank=True,
        default=STANDARD,
        null=False,
    )
    session = models.PositiveIntegerField(
        verbose_name=_("Session"), null=False, blank=False
    )
    diffusion = models.PositiveIntegerField(
        verbose_name=_("Diffusion"), null=True, blank=True
    )
    enrollment_start_date = models.DateField(verbose_name=_("Enrollment opening"))
    course_start_date = models.DateField(verbose_name=_("Course start date"))
    course_end_date = models.DateField(
        verbose_name=_("Course end date"), null=True, blank=True
    )
    enrollment_end_date = models.DateField(
        verbose_name=_("Enrollment closing"), null=True, blank=True
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Manager"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pre_courses",
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
    student_number = models.PositiveIntegerField(
        verbose_name=_("Student number"), null=True, blank=True
    )
    FUN_CAMPUS = "FUN_CAMPUS"
    FUN_CORPORATE = "FUN_CORPORATE"
    FUN_MOOC = "FUN_MOOC"
    PLATFORM_CHOICES = [
        (FUN_CAMPUS, _("FUN-CAMPUS")),
        (FUN_CORPORATE, _("FUN-CORPORATE")),
        (FUN_MOOC, _("FUN-MOOC")),
    ]
    plaform = models.CharField(
        verbose_name=_("Plaform"),
        max_length=max([len(e[0]) for e in PLATFORM_CHOICES]),
        choices=PLATFORM_CHOICES,
        null=False,
        blank=False,
    )
    LEVEL1 = "LEVEL1"
    LEVEL2 = "LEVEL2"
    LEVEL3 = "LEVEL3"
    NON_PROFIT_PARTNER = "NON_PROFIT_PARTNER"
    FOR_PROFIT_PARTNER = "FOR_PROFIT_PARTNER"
    PARTNER_BEYOND_QUOTA = "PARTNER_BEYOND_QUOTA"
    MEMBER_BEYOND_QUOTA = "MEMBER_BEYOND_QUOTA"
    THEME_PROJECT = "THEME_PROJECT"
    IRRELEVANT = "IRRELEVANT"
    MEMBERSHIP_LEVELS = [
        (LEVEL1, _("N1 - member level 1 subscription")),
        (LEVEL2, _("N2 - member level 2 subscription")),
        (LEVEL3, _("N3 - member level 3 subscription")),
        (NON_PROFIT_PARTNER, _("PA - non-profit partner")),
        (FOR_PROFIT_PARTNER, _("PP - for-profit partner")),
        (PARTNER_BEYOND_QUOTA, _("PHQ - partner beyond quota")),
        (MEMBER_BEYOND_QUOTA, _("NHQ - Member beyond quota (ex. State)")),
        (THEME_PROJECT, _("Theme project")),
        (IRRELEVANT, _("Irrelevant")),
    ]
    membership_level = models.CharField(
        verbose_name=_("Plaform"),
        max_length=max([len(e[0]) for e in MEMBERSHIP_LEVELS]),
        choices=MEMBERSHIP_LEVELS,
        null=False,
        blank=False,
    )
    organization_member = models.ForeignKey(
        Organization,
        verbose_name=_("Organization memeber"),
        help_text=_("the organization with membership"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pre_courses_as_member",
    )
    organization_lead = models.ForeignKey(
        Organization,
        verbose_name=_("Organization lead"),
        help_text=_("the organization leading the course"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pre_courses_as_lead",
    )
    organization_producer = models.ForeignKey(
        Organization,
        verbose_name=_("Organization producer"),
        help_text=_("the organization giving the course"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pre_courses_as_producer",
    )
    double_display = models.BooleanField(
        default=False,
        null=False,
        verbose_name=_("Double display"),
    )
    secondary_organization = models.ForeignKey(
        Organization,
        verbose_name=_("Secondary organization"),
        help_text=_("the second organization to display if double display is needed"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    summary = models.TextField(verbose_name=_("Summary"))
    contacts = models.TextField(verbose_name=_("Contacts"))
    email_addresses = models.TextField(verbose_name=_("Email addresses"))
    phone_numbers = models.TextField(verbose_name=_("Phone numbers"))
    week_duration = models.PositiveIntegerField(
        verbose_name=_("Week duration"),
        help_text=_("Duration of the course in week(s)"),
        null=True,
        blank=True,
    )
    estimated_weekly_hours = models.PositiveIntegerField(
        verbose_name=_("Estimated weekly hours"),
        help_text=_("The number of hour a student will need to work weekly"),
        null=True,
        blank=True,
    )
    comment = models.TextField(verbose_name=_("Comment"))
    attestation = models.BooleanField(
        verbose_name=_("Attestation"),
        null=True,
    )
    attestation_teachers = models.ManyToManyField(
        to=settings.AUTH_USER_MODEL,
        related_name="attestation_teacher_precourses",
        verbose_name=_("Attestation teachers"),
        blank=True,
    )
    test_attestation = models.CharField(
        verbose_name=_("Test attestation"), max_length=255, default="", blank=True
    )
    estimated_attestation_generation_date = models.DateField(
        verbose_name=_("Estimated attestation generation date"),
        help_text=_("The estimated date at which the attestation will be generated"),
        null=True,
        blank=True,
    )
    attestation_generation_date = models.DateField(
        verbose_name=_("Attestation generation date"),
        help_text=_("The date at which the attestation will be generated"),
        null=True,
        blank=True,
    )
    attestation_comment = models.TextField(verbose_name=_("Attestation comment"))
    delivered_attestation_quantity = models.PositiveIntegerField(
        verbose_name=_("Delivered attestation quantity"),
        null=True,
        blank=True,
    )
    registered_quantity = models.PositiveIntegerField(
        verbose_name=_("Registered quantity"),
        null=True,
        blank=True,
    )
    certificate = models.BooleanField(
        verbose_name=_("Certificate"),
        null=True,
    )
    IN_PERSON = "IN_PERSON"
    REMOTLY = "REMOTLY"
    SUBMISSION = "SUBMISSION"
    CERTIFICATE_TYPES = [
        (IN_PERSON, _("In person")),
        (REMOTLY, _("Remote observation")),
        (SUBMISSION, _("Project submission")),
    ]
    certificate_type = models.CharField(
        verbose_name=_("Certificate type"),
        max_length=max([len(e[0]) for e in CERTIFICATE_TYPES]),
        choices=CERTIFICATE_TYPES,
        null=False,
        blank=False,
    )
    exam_start_date = models.DateField(
        verbose_name=_("Exam start date"),
        null=True,
        blank=True,
    )
    exam_end_date = models.DateField(
        verbose_name=_("Exam end date"),
        null=True,
        blank=True,
    )
    payment_start_date = models.DateField(
        verbose_name=_("Payment start date"),
        null=True,
        blank=True,
    )
    payment_end_date = models.DateField(
        verbose_name=_("Payment end date"),
        null=True,
        blank=True,
    )
    exam_duration = models.DurationField(
        verbose_name=_("Exam duration"),
        null=True,
        blank=True,
    )
    exam_price = models.PositiveIntegerField(
        verbose_name=_("Exam price"),
        null=True,
        blank=True,
    )
    certificate_generation_date = models.DateField(
        verbose_name=_("Certificate generation date"),
        null=True,
        blank=True,
    )
    delivered_certificate_quantity = models.PositiveIntegerField(
        verbose_name=_("Delivered certificate quantity"),
        null=True,
        blank=True,
    )
    exam_url = models.URLField(verbose_name=_("Exam URL"), null=True, blank=True)
    certificate_comment = models.TextField(verbose_name=_("Certificate comment"))
    invoicing = models.TextField(verbose_name=_("Invoicing"))
    invoice_reference = models.CharField(
        verbose_name=_("Invoice reference"), max_length=255, default="", blank=True
    )
    invoicing_comment = models.TextField(verbose_name=_("Invoicing comment"))

    cohort_invoicing = models.CharField(
        verbose_name=_("Cohort invoicing"), max_length=255, default="", blank=True
    )
    member_invoicing = models.CharField(
        verbose_name=_("Member invoicing"), max_length=255, default="", blank=True
    )
    partner_invoicing = models.CharField(
        verbose_name=_("Partner invoicing"), max_length=255, default="", blank=True
    )
    invoicing_year = models.PositiveIntegerField(
        verbose_name=_("Invoicing year"),
        null=True,
        blank=True,
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
    precourse = models.ForeignKey(
        PreCourse,
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
