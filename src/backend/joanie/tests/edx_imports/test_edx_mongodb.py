"""Module for testing the edx_mongodb module."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from joanie.edx_imports import edx_mongodb


class TestGetEnrollment(TestCase):
    """Tests for the edx_mongodb module."""

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signatory_from_course_id(self, mock_mongo_client):
        """Test the get_signatory_from_course_id method."""
        course_id = "course-v1:fun+101+run01"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.active_versions.find_one.return_value = {
            "versions": {"published-branch": "branch_id"},
        }
        mock_mongo_client.return_value.edxapp.modulestore.structures.find_one.return_value = {
            "_id": "branch_id",
            "blocks": [
                {
                    "block_type": "course",
                    "fields": {
                        "certificates": {
                            "certificates": [{"signatories": ["test_signatory"]}]
                        }
                    },
                }
            ],
        }

        result = edx_mongodb.get_signatory_from_course_id(course_id)

        self.assertEqual(result, "test_signatory")

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signatory_from_course_id_no_certificates(
        self, mock_mongo_client
    ):
        """Test the get_signatory_from_course_id method when there are no certificates."""
        course_id = "course-v1:fun+101+run01"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.active_versions.find_one.return_value = {
            "versions": {"published-branch": "branch_id"},
        }
        mock_mongo_client.return_value.edxapp.modulestore.structures.find_one.return_value = {
            "_id": "branch_id",
            "blocks": [],
        }

        result = edx_mongodb.get_signatory_from_course_id(course_id)

        self.assertEqual(result, None)

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signatory_from_course_id_no_signatories(
        self, mock_mongo_client
    ):
        """Test the get_signatory_from_course_id method when there are no signatories."""
        course_id = "fun/101/run01"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.active_versions.find_one.return_value = {
            "versions": {"published-branch": "branch_id"},
        }
        mock_mongo_client.return_value.edxapp.modulestore.structures.find_one.return_value = {
            "_id": "branch_id",
            "blocks": [
                {
                    "block_type": "course",
                    "fields": {"certificates": {"certificates": [{"signatories": []}]}},
                }
            ],
        }

        result = edx_mongodb.get_signatory_from_course_id(course_id)

        self.assertEqual(result, None)

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signatory_from_course_id_no_course_block(
        self, mock_mongo_client
    ):
        """Test the get_signatory_from_course_id method when there is no course block."""
        course_id = "course-v1:fun+101+run01"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.active_versions.find_one.return_value = {
            "versions": {"published-branch": "branch_id"},
        }
        mock_mongo_client.return_value.edxapp.modulestore.structures.find_one.return_value = None

        result = edx_mongodb.get_signatory_from_course_id(course_id)

        self.assertEqual(result, None)

    @patch("joanie.edx_imports.edx_mongodb.MongoClient")
    def test_edx_mongodb_get_signatory_from_course_id_no_result(
        self, mock_mongo_client
    ):
        """Test the get_signatory_from_course_id method when there is no enrollment."""
        course_id = "course-v1:fun+101+run01"
        mock_mongo_client.return_value = MagicMock()
        mock_mongo_client.return_value.edxapp.modulestore.active_versions.find_one.return_value = None  # pylint: disable=line-too-long

        result = edx_mongodb.get_signatory_from_course_id(course_id)

        self.assertEqual(result, None)
