"""
Test suite for extra template tags of the joanie core app
"""
from django.test import TestCase

from joanie.core.templatetags.extra_tags import base64_static


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
