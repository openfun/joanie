"""
Test suite for Event delete API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class EventDeleteApiTest(BaseAPITestCase):
    """
    Test suite for Event delete API endpoint.
    """

    def test_api_event_delete_anonymous(self):
        """
        Anonymous users should not delete event
        """
        event = factories.EventFactory()
        response = self.client.delete(f"/api/v1.0/events/{event.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_event_delete_no_events(self):
        """
        User should not delete not owned event
        """
        user = factories.UserFactory()
        event = factories.EventFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/events/{event.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_event_delete_with_events(self):
        """
        User should not access their event details
        """
        user = factories.UserFactory()
        event = factories.EventFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/events/{event.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
