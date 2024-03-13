"""
This module contains the base classes for creating filters with multiple values.

The `MultipleValueField` class is a subclass of `MultipleChoiceField` and provides additional
functionality for handling multiple values. It allows for validation and cleaning of individual
values.

The `MultipleValueFilter` class is a filter that allows multiple values for a specific field.
It sets the default lookup expression to 'in', which checks if the field's value is in the provided
list of values.
"""

from django.forms.fields import MultipleChoiceField

from django_filters.filters import Filter


class MultipleValueField(MultipleChoiceField):
    """
    A field that allows multiple values.

    This field is a subclass of MultipleChoiceField and provides additional functionality
    for handling multiple values.

    Args:
        field_class: The class of the inner field used to validate and clean individual values.

    Attributes:
        inner_field: An instance of the inner field class used to validate and clean individual
        values.
    """

    def __init__(self, *args, field_class, **kwargs):
        self.inner_field = field_class()
        super().__init__(*args, **kwargs)

    def valid_value(self, value):
        """
        Check if a value is valid.

        Args:
            value: The value to be checked.

        Returns:
            bool: True if the value is valid, False otherwise.
        """
        return self.inner_field.validate(value)

    def clean(self, value):
        """
        Clean the given values.

        Args:
            value: A list of values to be cleaned.

        Returns:
            list: A list of cleaned values.
        """
        return value and [self.inner_field.clean(v) for v in value]


class MultipleValueFilter(Filter):
    """
    A filter that allows multiple values for a field.

    This filter is used to filter querysets based on multiple values for a specific field.
    It sets the default lookup expression to 'in', which checks if the field's value is in the
    provided list of values.

    Args:
        *args: Variable length argument list.
        field_class: The class of the field to be filtered.
        **kwargs: Arbitrary keyword arguments.

    Attributes:
        field_class: The class of the field to be filtered.

    """

    field_class = MultipleValueField

    def __init__(self, *args, field_class, **kwargs):
        """
        Initializes a new instance of the MultipleValueFilter class.

        Args:
            *args: Variable length argument list.
            field_class: The class of the field to be filtered.
            **kwargs: Arbitrary keyword arguments.

        """
        kwargs.setdefault("lookup_expr", "in")
        super().__init__(*args, field_class=field_class, **kwargs)
