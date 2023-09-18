"""Test suite for the "synchronize_signed_document" utility"""
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from joanie.core.utils import webhooks


class SynchronizeSignedDocumentUtilsTestCase(TestCase):
    """Test suite for the `synchronize_signed_document` utility."""

    def _get_request_from_signature_provider(self, event):
        """
        Return a short example of the body of a POST request received by the API
        with an event type from the signature provider.
        """
        return {
            "eventType": str(event),
            "id": "wbe_test_synchronize_1",
            "workflowId": "wlf_dummy_test",
        }

    def test_utils_synchronize_signed_document_workflow_finished_event(self):
        """
        If the request method is POST, and it has the event type 'workflowFinished',
        the webhook synchronize method should return a status code 200.
        """
        expected_response_data = {
            "status": "Successful document with signatures: wlf_dummy_test"
        }
        request = APIRequestFactory().post(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("workflowFinished"),
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_response_data)

    def test_utils_synchronize_signed_document_recipient_refused_event(self):
        """
        If the request method is POST, and it has the event type 'recipientRefused',
        the webhook synchronize method should return a status code 200.
        """
        expected_response_data = {"status": "Refused document signature wlf_dummy_test"}
        request = APIRequestFactory().post(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("recipientRefused"),
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_response_data)

    def test_utils_synchronize_signed_document_started_event_type(self):
        """
        If the request method is POST, and it has the wrong event type,
        the webhook synchronize method should return a status code 400.
        """
        expected_response_data = {"status": "Incorrect event type 'workflowStarted'"}

        request = APIRequestFactory().post(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("workflowStarted"),
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, expected_response_data)

    def test_utils_synchronize_signed_document_with_no_body_payload(self):
        """
        If the request method is POST, and it has no body, when using json.loads()
        with no body, the webhook synchronize should return a status code 400
        when the exception JSONDecodeError occurs.
        """
        expected_response_data = {
            "error": "Missing data from the body of the POST request"
        }

        request = APIRequestFactory().post(
            path="/webhook-signature",
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, expected_response_data)

    def test_utils_synchronize_signed_document_wrong_request_methods(self):
        """
        If the request method is GET/PATCH/PUT, and even if it has the correct event type,
        the webhook synchronize method should return a status code 405.
        If the request method is POST with an unauthorized event, it should
        return a status code 400.
        """
        expected_response_data = {"error": "Invalid request method"}

        request = APIRequestFactory().get(
            path="/webhook-signature",
            data={},
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data, expected_response_data)

        request = APIRequestFactory().put(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("workflowFinished"),
            format="json",
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data, expected_response_data)

        request = APIRequestFactory().patch(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("recipientRefused"),
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data, expected_response_data)

        request = APIRequestFactory().post(
            path="/webhook-signature",
            data=self._get_request_from_signature_provider("recipientFinished"),
        )
        response = webhooks.synchronize_signed_document(request)
        self.assertEqual(response.status_code, 400)
