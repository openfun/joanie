"""
Core application forms declaration
"""
from django import forms
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from joanie.core import models


class ProductCourseRelationAdminForm(forms.ModelForm):
    """
    The admin form for the ProductCourseRelation model.

    This is a customized form in order to filter the list of course runs to
    their which relies on the course instance.
    """

    course_runs = forms.ModelMultipleChoiceField(
        queryset=models.CourseRun.objects.none(),
        widget=widgets.FilteredSelectMultiple(
            models.CourseRun._meta.verbose_name_plural, is_stacked=False
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        if instance is not None:
            queryset = models.CourseRun.objects.filter(
                Q(course=instance.course) | Q(pk__in=instance.course_runs.all())
            )
            self.fields["course_runs"].queryset = queryset


class CourseRunAdminForm(forms.ModelForm):
    """
    The admin form for the CourseRun model.

    It implements a clean_course method to prevent integrity error. In fact update
    course_run has to be forbid if the course run is joined to a product or an order.
    """

    def clean_course(self):
        """
        If user tries to update the course field, check that
        course_run.product_relations and course_run.order_relations are empties.
        """
        course = self.cleaned_data["course"]
        if "course" in self.changed_data:
            resource_link = self.data["resource_link"]
            if models.CourseRun.objects.filter(
                (Q(product_relations__isnull=False) | Q(order_relations__isnull=False)),
                resource_link=resource_link,
            ).exists():
                raise ValidationError(
                    _(
                        "This course run relies on a product relation. "
                        "So you cannot modify its course."
                    )
                )

        return course
