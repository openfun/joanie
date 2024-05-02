"""
Test suite for the util file_checksum of the joanie core app
"""

from django.core.files.base import ContentFile
from django.test import TestCase

from joanie.core.utils import file_checksum


class UtilsTestCase(TestCase):
    """Test suite for utils."""

    def test_utils_file_checksum(self):
        """Checksum from a file."""
        file = ContentFile("")
        checksum = file_checksum(file)

        self.assertEqual(len(checksum), 64)
        self.assertEqual(
            checksum,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
