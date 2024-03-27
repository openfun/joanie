"""
Brevo API client test module.
"""

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from django.conf import settings
from django.test import TestCase, override_settings

import responses

from joanie.core.factories import UserFactory
from joanie.core.utils.newsletter.brevo import Brevo


@override_settings(
    BREVO_API_KEY="api-key", BREVO_COMMERCIAL_NEWSLETTER_LIST_ID="list-id"
)
class BrevoTestCase(TestCase):
    """
    Brevo API client test case.
    """

    def setUp(self):
        base_url = settings.BREVO_API_URL
        list_id = settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID
        self.create_contact_url = f"{base_url}contacts"
        list_contacts_url = f"{base_url}contacts/lists/{list_id}/contacts"
        self.subscribe_to_list_url = f"{list_contacts_url}/add"
        self.unsubscribe_from_list_url = f"{list_contacts_url}/remove"

    @responses.activate(assert_all_requests_are_fired=True)
    def test_create_contact_to_commercial_list_ok(self):
        """
        Test the creation of a contact in the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        json_response = {"id": "contact-id"}
        responses.add(
            responses.POST,
            self.create_contact_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "email": user.email,
                        "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user)
        response = brevo_user.create_contact_to_commercial_list()

        self.assertEqual(json_response, response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_subscribe_to_commercial_list_exists(self):
        """
        Test the removal of a contact from the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        json_response = {"contacts": {"failure": [], "success": ["user@example.com"]}}
        responses.add(
            responses.POST,
            self.subscribe_to_list_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "emails": [user.email],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user)
        response = brevo_user.subscribe_to_commercial_list()

        self.assertEqual(json_response, response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_subscribe_to_commercial_list_create(self):
        """
        Test the removal of a contact from the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        responses.add(
            responses.POST,
            self.subscribe_to_list_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "emails": [user.email],
                    }
                ),
            ],
            status=400,
            json={"code": "invalid_parameter"},
        )

        json_response = {"id": "contact-id"}
        responses.add(
            responses.POST,
            self.create_contact_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "email": user.email,
                        "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user)
        response = brevo_user.subscribe_to_commercial_list()

        self.assertEqual(json_response, response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_unsubscribe_from_commercial_list_ok(self):
        """
        Test the removal of a contact from the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        json_response = {"contacts": {"failure": [], "success": ["user@example.com"]}}
        responses.add(
            responses.POST,
            self.unsubscribe_from_list_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "emails": [user.email],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user)
        response = brevo_user.unsubscribe_from_commercial_list()

        self.assertEqual(json_response, response)
