"""Joanie Core application"""

from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_save
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Configuration class for the joanie core app."""

    name = "joanie.core"
    verbose_name = _("Joanie's core application")

    # pylint: disable=import-outside-toplevel
    def ready(self):
        """Register signals."""
        from joanie.core import models, signals

        post_save.connect(
            signals.on_save_course_run,
            sender=models.CourseRun,
            dispatch_uid="save_course_run",
        )
        post_save.connect(
            signals.on_save_product_target_course_relation,
            sender=models.ProductTargetCourseRelation,
            dispatch_uid="save_product_target_course_relation",
        )
        m2m_changed.connect(
            signals.on_change_course_product_relation,
            sender=models.Course.products.through,
            dispatch_uid="m2m_changed_course_product_relation",
        )
        m2m_changed.connect(
            signals.on_change_course_runs_to_product_target_course_relation,
            sender=models.ProductTargetCourseRelation.course_runs.through,
            dispatch_uid="m2m_changed_product_target_course_relation_course_runs",
        )
        return super().ready()
