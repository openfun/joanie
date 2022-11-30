"""
Core application forms declaration
"""
from django import forms
from django.contrib.admin import widgets

from joanie.core import models


class ProductTargetCourseRelationAdminForm(forms.ModelForm):
    """
    The admin form for the ProductTargetCourseRelation model.

    This is a customized form in order to filter the list of course runs to
    those related to the course instance.
    """

    course_runs = forms.ModelMultipleChoiceField(
        queryset=models.CourseRun.objects.none(),
        widget=widgets.FilteredSelectMultiple(
            models.CourseRun._meta.verbose_name_plural, is_stacked=False
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize the admin form of the ProductTargetCourseRelation model.

        In the case where user is editing an existing instance, we populate choices of
        the "course_runs" field with course runs of the related course.
        """
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        if instance is not None:
            # Get all course runs related to the course instance.
            queryset = models.CourseRun.objects.filter(course=instance.course)
            self.fields["course_runs"].queryset = queryset
