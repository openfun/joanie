
from django.db import models
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models


class Organization(parler_models.TranslatableModel):
    """
    Organization is required to create course page in cms,
    useful in the future to validate inscription or not depend on school level for example
    """
    code = models.CharField(verbose_name=_("code"), unique=True, max_length=100)
    translations = parler_models.TranslatedFields(
        title=models.CharField(verbose_name=_("title"), max_length=255)
    )

    class Meta:
        db_table = "joanie_organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return f"{self.code} - {self.title}"


class Course(parler_models.TranslatableModel):
    """ A new course created will initialize a cms page """
    code = models.CharField(verbose_name=_("reference to cms page"), max_length=100, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(verbose_name=_("title"), max_length=255)
    )
    organization = models.ForeignKey(
        Organization, verbose_name=_("organization"), on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "joanie_course"
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return f"Course \"{self.title}\" [{self.code}]"


class CourseRun(parler_models.TranslatableModel):
    resource_link = models.CharField(_("resource link"), max_length=200, blank=True, null=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(verbose_name=_("title"), max_length=255)
    )
    start = models.DateTimeField(_("start date"))
    end = models.DateTimeField(_("end date"))
    enrollment_start = models.DateTimeField(_("enrollment date"), null=True)
    enrollment_end = models.DateTimeField(_("enrollment end"), null=True)

    class Meta:
        db_table = "joanie_course_run"
        verbose_name = _("Course run")
        verbose_name_plural = _("Course runs")

    def __str__(self):
        return f"Session \"{self.title}\" [{self.start:%Y-%m-%d} to {self.end:%Y-%m-%d}]"
