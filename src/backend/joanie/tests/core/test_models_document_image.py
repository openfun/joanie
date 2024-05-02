"""Test suite for DocumentImage Model"""

from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import TestCase

from joanie.core.models import DocumentImage


class DocumentImageModelTestCase(TestCase):
    """DocumentImage model test case."""

    def test_models_document_image_checksum_set_on_save(self):
        """
        When a DocumentImage is created, the checksum should be calculated
        and set if it is no defined
        """
        file = ContentFile(content=b"", name="test.txt")
        image = DocumentImage.objects.create(file=file)
        self.assertEqual(
            image.checksum,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_models_document_image_checksum_not_set_on_save_if_exists(self):
        """
        When a DocumentImage is created, the checksum should not be calculated
        if it is defined.
        """
        file = ContentFile(content=b"", name="test.txt")
        image = DocumentImage.objects.create(file=file, checksum="123abc")

        self.assertEqual(image.checksum, "123abc")

    def test_models_document_image_checksum_unique(self):
        """DocumentImage checksum should be unique."""

        file = ContentFile(content=b"", name="test.txt")
        DocumentImage.objects.create(file=file, checksum="123abc")

        with self.assertRaises(IntegrityError) as context:
            DocumentImage.objects.create(file=file, checksum="123abc")

        self.assertEqual(
            str(context.exception),
            (
                'duplicate key value violates unique constraint "core_documentimage_checksum_key"\n'
                "DETAIL:  Key (checksum)=(123abc) already exists."
            ),
        )
