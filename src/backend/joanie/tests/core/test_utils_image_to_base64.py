"""
Test suite for utils of the joanie core app
"""
import io

from django.test import TestCase

from joanie.core import factories, utils

BLUE_SQUARE_BASE64 = (
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgY"
    "PgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
)


class UtilsTestCase(TestCase):
    """Test suite for utils."""

    def test_utils_image_to_base64_file_closed(self):
        """Image to base64 from closed file."""
        organization = factories.OrganizationFactory()
        logo = organization.logo

        self.assertEqual(utils.image_to_base64(logo), BLUE_SQUARE_BASE64)
        self.assertEqual(logo.tell(), 0)

    def test_utils_image_to_base64_file_opened(self):
        """Image to base64 from opened file."""
        organization = factories.OrganizationFactory()
        logo = organization.logo
        with logo.open() as logo_file:
            logo_file.seek(3)

            self.assertEqual(utils.image_to_base64(logo_file), BLUE_SQUARE_BASE64)

            self.assertEqual(logo_file.tell(), 3)

    def test_utils_image_to_base64_path(self):
        """Image to base64 from path."""
        organization = factories.OrganizationFactory()

        self.assertEqual(
            utils.image_to_base64(organization.logo.path), BLUE_SQUARE_BASE64
        )

    def test_utils_image_to_base64_path_not_found(self):
        """Image to base64 from path that does not exist."""
        self.assertEqual(utils.image_to_base64("not_found.png"), "")

    def test_utils_image_to_base64_file_empty(self):
        """Image to base64 from empty file."""
        empty_file = io.BytesIO()
        self.assertEqual(utils.image_to_base64(empty_file), "")

    def test_utils_image_to_base64_file_not_image(self):
        """Image to base64 from a file that is not an image."""
        text_file = io.BytesIO("this is not an image".encode("utf-8"))
        self.assertEqual(utils.image_to_base64(text_file), "")
