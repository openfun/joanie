"""
Declare and configure the models for the wishlist part
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from . import Course, User
from .base import BaseModel


class CourseWish(BaseModel):
    """
    CourseWish represents and records a user wish to participate at a course
    """

    owner = models.ForeignKey(
        to=User,
        verbose_name=_("Owner"),
        related_name="wishlist",
        on_delete=models.PROTECT,
    )

    course = models.ForeignKey(
        to=Course,
        verbose_name=_("Course"),
        related_name="wished_in_wishlists",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "joanie_course_wish"
        verbose_name = _("Course Wish")
        verbose_name_plural = _("Course Wishes")
        unique_together = ("owner", "course")

    def __str__(self):
        return f"{self.owner}'s wish to participate at the course {self.course}"
