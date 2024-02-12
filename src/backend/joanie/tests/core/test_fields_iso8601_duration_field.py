"""Test suite for the ISO8601DurationField for serializers"""
from datetime import timedelta

from django.test import TestCase

from joanie.core.serializers.fields import ISO8601DurationField


class TestISO8601DurationField(TestCase):
    """Test suite for the ISO8601DurationField for serializers"""

    def test_fields_iso8601_duration_field_to_representation_method(self):
        """
        Test `to_representation` method from the custom field ISO8601DurationField
        when the input value is timedelta, it should output the value as ISO 8601 format.
        """
        field = ISO8601DurationField()
        timedelta_value = timedelta(seconds=36000)  # represents 10 hours in ISO 8601

        result = field.to_representation(timedelta_value)

        self.assertEqual(result, "PT10H")
        self.assertIsInstance(result, str)

    def test_fields_iso8601_duration_field_to_internal_value_method(self):
        """
        Test `to_internal_value` method from the custom field ISO8601DurationField
        when the input value is ISO 8601 format, it should output the value as
        timedelta type.
        """
        field = ISO8601DurationField()
        iso8601_value = "PT10H"  # represents 10 hours in ISO 8601

        result = field.to_internal_value(iso8601_value)

        self.assertEqual(result, timedelta(seconds=36000))
        self.assertEqual(str(result), "10:00:00")
        self.assertIsInstance(result, timedelta)
