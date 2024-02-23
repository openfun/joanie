"""
Test suite for Event list API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class EventListApiTest(BaseAPITestCase):
    """
    Test suite for Event list API endpoint.
    """

    def test_api_event_list_anonymous(self):
        """
        Anonymous users should not be able to get events
        """
        factories.EventFactory()
        response = self.client.get("/api/v1.0/events/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_event_list_user(self):
        """
        User should see only their events
        """
        user = factories.UserFactory()
        user_events = factories.EventFactory.create_batch(3, user=user)
        factories.EventFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/events/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(event.id),
                        "message": event.message,
                        "level": event.level,
                        "created_on": format_date(event.created_on),
                    }
                    for event in user_events
                ],
            },
        )
