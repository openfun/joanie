"""
Declare and configure models for course wishes
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from joanie.core.models.base import BaseModel


class CourseWish(BaseModel):
    """
    CourseWish represents and records a user wish to participate in a course
    """

    owner = models.ForeignKey(
        to="User",
        verbose_name=_("Owner"),
        related_name="course_wishes",
        on_delete=models.PROTECT,
    )

    course = models.ForeignKey(
        to="Course",
        verbose_name=_("Course"),
        related_name="wishes",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "joanie_course_wish"
        verbose_name = _("Course Wish")
        verbose_name_plural = _("Course Wishes")
        unique_together = ("owner", "course")

    def __str__(self):
        return f"{self.owner}'s wish to participate in {self.course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)
