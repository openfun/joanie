"""
Test suite for Event retrieve API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class EventRetrieveApiTest(BaseAPITestCase):
    """
    Test suite for Event retrieve API endpoint.
    """

    def test_api_event_retrieve_anonymous(self):
        """
        Anonymous users should not access event details
        """
        event = factories.EventFactory()
        response = self.client.get(f"/api/v1.0/events/{event.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_event_retrieve_no_events(self):
        """
        User should not access event details
        """
        user = factories.UserFactory()
        event = factories.EventFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/events/{event.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_event_retrieve_with_events(self):
        """
        User should not access their event details
        """
        user = factories.UserFactory()
        event = factories.EventFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/events/{event.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
