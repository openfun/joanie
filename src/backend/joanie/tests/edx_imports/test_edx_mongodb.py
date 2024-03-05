"""Module for testing the edx_mongodb module."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from joanie.edx_imports import edx_mongodb


class TestGetEnrollment(TestCase):
    """Tests for the edx_mongodb module."""

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signature_from_enrollment(self, mock_mongo_client):
        """Test the get_signature_from_enrollment method."""
        course_id = "test_course"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.find_one.return_value = {
            "_id": {"org": "test_org", "category": "course", "course": course_id},
            "metadata": {
                "certificates": {"certificates": [{"signatories": ["test_signatory"]}]}
            },
        }

        result = edx_mongodb.get_signature_from_enrollment(course_id)

        self.assertEqual(result, "test_signatory")

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signature_from_enrollment_no_certificates(
        self, mock_mongo_client
    ):
        """Test the get_signature_from_enrollment method when there are no certificates."""
        course_id = "test_course"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.find_one.return_value = {
            "_id": {"org": "test_org", "category": "course", "course": course_id},
            "metadata": {},
        }

        result = edx_mongodb.get_signature_from_enrollment(course_id)

        self.assertEqual(result, None)

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signature_from_enrollment_no_signatories(
        self, mock_mongo_client
    ):
        """Test the get_signature_from_enrollment method when there are no certificates."""
        course_id = "test_course"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.find_one.return_value = {
            "_id": {"org": "test_org", "category": "course", "course": course_id},
            "metadata": {"certificates": {"certificates": []}},
        }

        result = edx_mongodb.get_signature_from_enrollment(course_id)

        self.assertEqual(result, None)

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signature_from_enrollment_no_result(
        self, mock_mongo_client
    ):
        """Test the get_signature_from_enrollment method when there is no enrollment."""
        course_id = "test_course"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.find_one.return_value = None

        result = edx_mongodb.get_signature_from_enrollment(course_id)

        self.assertEqual(result, None)
