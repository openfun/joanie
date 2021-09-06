"""
Declare and configure the models for the courses part
"""
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models
from url_normalize import url_normalize

from joanie.core import utils
from joanie.core.enums import ALL_LANGUAGES
from joanie.core.fields.multiselect import MultiSelectField


class Organization(parler_models.TranslatableModel):
    """
    Organization model represents and records entities that manage courses.
    It could be a university or a training company for example.
    It's required to create course page in cms.
    It will allow to validate user enrollment to course or not, depending on various criteria.
    """

    code = models.CharField(_("code"), unique=True, db_index=True, max_length=100)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    representative = models.CharField(
        _("representative"),
        help_text=_("representative fullname (to sign certificate for example)"),
        max_length=100,
        blank=True,
    )
    signature = models.ImageField(_("signature"), blank=True)
    logo = models.ImageField(_("logo"), blank=True)

    class Meta:
        db_table = "joanie_organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return (
            f"[{self.code}] {self.safe_translation_getter('title', any_language=True)}"
        )


class Course(parler_models.TranslatableModel):
    """
    Course model represents and records a course in the cms catalog.
    A new course created will initialize a cms page.
    """

    code = models.CharField(_("code"), max_length=100, unique=True, db_index=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("organization"),
        on_delete=models.PROTECT,
    )
    products = models.ManyToManyField(
        "Product",
        related_name="courses",
        verbose_name=_("products"),
        blank=True,
    )

    class Meta:
        db_table = "joanie_course"
        ordering = ("code",)
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness
        """
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def save(self, *args, **kwargs):
        """
        Enforce validation each time an instance is saved
        """
        self.full_clean()
        super().save(*args, **kwargs)


class CourseRun(parler_models.TranslatableModel):
    """
    Course run represents and records the occurrence of a course between a start
    and an end date.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="course_runs",
        verbose_name=_("course"),
    )

    # link to lms resource
    resource_link = models.CharField(_("resource link"), max_length=200, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    # availability period
    start = models.DateTimeField(_("course start"), blank=True, null=True)
    end = models.DateTimeField(_("course end"), blank=True, null=True)
    # enrollment allowed period
    enrollment_start = models.DateTimeField(_("enrollment date"), blank=True, null=True)
    enrollment_end = models.DateTimeField(_("enrollment end"), blank=True, null=True)
    languages = MultiSelectField(
        max_choices=50,
        max_length=255,  # MySQL does not allow max_length > 255
        # Language choices are made lazy so that we can override them in our tests.
        # When set directly, they are evaluated too early and can't be changed with the
        # "override_settings" utility.
        choices=lazy(lambda: ALL_LANGUAGES, tuple)(),
        help_text=_("The list of languages in which the course content is available."),
    )

    class Meta:
        db_table = "joanie_course_run"
        verbose_name = _("Course run")
        verbose_name_plural = _("Course runs")

    def __str__(self):
        return (
            f"{self.safe_translation_getter('title', any_language=True)} "
            f"[{self.start:%Y-%m-%d} to {self.end:%Y-%m-%d}]"
        )

    def clean(self):
        """Normalize the resource_link url."""
        self.resource_link = url_normalize(self.resource_link)
        super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        super().save(*args, **kwargs)
