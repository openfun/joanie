"""
Test suite for extra template tags of the joanie core app
"""
from django.test import TestCase

from joanie.core.templatetags.extra_tags import base64_static, join_and, list_key


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
