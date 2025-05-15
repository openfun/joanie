"""
Core application forms declaration
"""

from django import forms
from django.contrib.admin import widgets

from joanie.core import models


class CourseProductRelationAdminForm(forms.ModelForm):
    """
    The admin form for the CourseProductRelation model.
    """

    organizations = forms.ModelMultipleChoiceField(
        queryset=models.Organization.objects.all(),
        widget=widgets.FilteredSelectMultiple(
            models.Organization._meta.verbose_name_plural,  # noqa: SLF001
            is_stacked=False,
        ),
        required=True,
    )

    class Meta:
        fields = ["course", "product", "organizations"]
        model = models.CourseProductRelation


class ProductTargetCourseRelationAdminForm(forms.ModelForm):
    """
    The admin form for the ProductTargetCourseRelation model.

    This is a customized form in order to filter the list of course runs to
    those related to the course instance.
    """

    course_runs = forms.ModelMultipleChoiceField(
        queryset=models.CourseRun.objects.none(),
        widget=widgets.FilteredSelectMultiple(
            models.CourseRun._meta.verbose_name_plural,  # noqa: SLF001
            is_stacked=False,
        ),
        required=False,
    )

    class Meta:
        fields = ["course", "product", "position", "course_runs"]
        model = models.ProductTargetCourseRelation

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


class BatchOrderAdminForm(forms.ModelForm):
    """
    This is a customized form to handle voucher code that is passed during creation or editing
    a batch order.
    """

    voucher = forms.CharField(
        required=False,
        help_text="Enter a voucher code",
        label="Voucher code",
    )
    trainees = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        help_text="Enter one full name per line, e.g.:<br>John Doe<br>Jane Smith",
        label="Trainees",
    )

    class Meta:
        fields = [
            "organization",
            "owner",
            "company_name",
            "identification_number",
            "address",
            "city",
            "postcode",
            "country",
            "relation",
            "nb_seats",
            "voucher",
            "trainees",
        ]
        model = models.BatchOrder

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. For voucher, return the voucher code instead
        of the id, and for the trainees return in a more human-friendly format instead of JSON.
        """
        value = super().get_initial_for_field(field, field_name)

        if field_name == "trainees" and value:
            value = "\n".join(
                f"{trainee.get('first_name')} {trainee.get('last_name')}"
                for trainee in value
            )
        if field_name == "voucher" and value:
            value = models.Voucher.objects.get(id=value).code

        return value

    def clean_voucher(self):
        """
        Convert the entered voucher code to a Voucher object, or raise an error if not found.
        If no code is provided, the field is left unset.
        """
        voucher_info = self.cleaned_data.get("voucher")
        if not voucher_info:
            return None

        try:
            voucher = models.Voucher.objects.get(code=voucher_info)
        except models.Voucher.DoesNotExist as exception:
            raise forms.ValidationError("Voucher code not found.") from exception

        return voucher

    def clean_trainees(self):
        """
        Convert the trainees fullnames in the format awaited by the field `trainees`
        of the BatchOrder model.
        """
        trainees_data = self.cleaned_data.get("trainees")
        trainees_fullnames = trainees_data.strip().splitlines()

        trainees = []
        for trainee_fullname in trainees_fullnames:
            # Force the split after the first occurence of a space because long lastname exists
            first_name, last_name = trainee_fullname.split(" ", 1)
            trainees.append({"first_name": first_name, "last_name": last_name})

        return trainees
