"""
Test suite for extra template tags of the joanie core app
"""
import random

from django.test import TestCase

from joanie.core.templatetags.extra_tags import (
    base64_static,
    iso8601_to_duration,
    join_and,
    list_key,
)


class TemplateTagsExtraTagsTestCase(TestCase):
    """Test suite for extra template tags."""

    def test_templatetags_extra_tags_base64_static(self):
        """
        The template tags `base64_static` should return a static file encoded in base64.
        """
        static_filepath = "joanie/red-square.webp"

        red_square_base64 = (
            "data:image/webp;base64, UklGRjAAAABXRUJQVlA4ICQAAABwAQCdASoBAAEACTD+J7ACdA"
            "FAAAD+0MkjDRr8XewjvuzAAAA="
        )

        self.assertEqual(base64_static(static_filepath), red_square_base64)

    def test_templatetags_extra_tags_base64_static_unknown_static(self):
        """
        The template tags `base64_static` should return an empty string.
        """
        static_filepath = "unknown-static-file.txt"
        self.assertEqual(base64_static(static_filepath), "")

    def test_templatetags_extra_tags_join_and(self):
        """
        The template tags `join_and` should join a list of items in a human-readable way
        """
        # - Test with a single item
        items = ["Joanie"]
        self.assertEqual(join_and(items), "Joanie")

        # - Test with two items
        items += ["Richie"]
        self.assertEqual(join_and(items), "Joanie and Richie")

        # - Test with three items
        items += ["Fonzie"]
        self.assertEqual(join_and(items), "Joanie, Richie and Fonzie")

        # - Test with four items
        items += ["Marsha"]
        self.assertEqual(join_and(items), "Joanie, Richie, Fonzie and Marsha")

    def test_templatetags_extra_tags_list_key(self):
        """
        The template tags `list_key` should return a list of values from a list of
        dictionaries.
        """
        data = [
            {"username": "joanie"},
            {"username": "richie"},
            {"username": "fonzie"},
            {"username": "marsha"},
        ]

        self.assertEqual(
            list_key(data, "username"), ["joanie", "richie", "fonzie", "marsha"]
        )

    def test_templatetags_extra_tags_iso8601_to_duration_fails_because_input_value_is_not_iso8601(
        self,
    ):
        """
        The template tags `iso8601_to_duration` should return an empty string if the input value is
        not ISO 8601 compliant. ISO 8601 durations should follow the format "PnYnMnDTnHnMnS,
        where each component is optional, but they should appear in the correct order.
        """
        iso8601_duration = random.choice(
            ["10H40M55S", "P10H30M60S", "P1W5D", "P3YM6M", "P1.5H", "P22H40S39M"]
        )

        with self.assertRaises(ValueError) as context:
            iso8601_to_duration(duration=iso8601_duration, unit="hours")

        self.assertEqual(
            str(context.exception),
            f"Duration input '{iso8601_duration}' is not ISO 8601 compliant.",
        )

    def test_templatetags_extra_tags_iso8601_to_duration_in_seconds(self):
        """
        The template tags `iso8601_to_duration` should return in seconds the duration
        in ISO 8601 format.
        """
        iso8601_duration = "PT10H"

        result = iso8601_to_duration(duration=iso8601_duration, unit="seconds")

        self.assertEqual(result, 36000)

    def test_templatetags_extra_tags_iso8601_to_duration_to_minutes(self):
        """
        The template tags `iso8601_to_duration` should return in minutes the duration in
        ISO 8601 format.
        """
        iso8601_duration = "PT10H30M"

        result = iso8601_to_duration(duration=iso8601_duration, unit="minutes")

        self.assertEqual(result, 630)

    def test_templatetags_extra_tags_iso8601_to_duration_in_hours(self):
        """
        The template tags `iso8601_to_duration` should return in hours the duration in ISO 8601
        format. The value will represent the hours that will be rounded up.
        """
        iso8601_duration = random.choice(
            ["PT10H01M", "PT10H10M", "PT10H20M", "PT10H40M", "PT10H59M"]
        )

        result = iso8601_to_duration(duration=iso8601_duration, unit="hours")

        self.assertEqual(result, 11)
