"""
Test suite for Event create API endpoint.
"""
from http import HTTPStatus

from joanie.tests.base import BaseAPITestCase


class EventCreateApiTest(BaseAPITestCase):
    """
    Test suite for Event create API endpoint.
    """

    def test_api_event_create_anonymous(self):
        """
        Anonymous users should not be able to get events
        """
        data = {
            "type": enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
            "level": enums.EVENT_INFO,
        }
        response = self.client.post(
            "/api/v1.0/events/", data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
