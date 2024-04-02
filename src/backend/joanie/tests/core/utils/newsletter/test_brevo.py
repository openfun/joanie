# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""
Brevo API client test module.
"""

from urllib.parse import quote_plus

from django.conf import settings
from django.test import TestCase, override_settings

import responses

from joanie.core.factories import UserFactory
from joanie.core.utils.newsletter.brevo import Brevo

BREVO_CONTACTS_LIST = {
    "contacts": [
        {
            "email": "user_1@example.com",
            "id": 53960194,
            "emailBlacklisted": False,
            "smsBlacklisted": False,
            "createdAt": "2024-03-29T15:22:28.604+01:00",
            "modifiedAt": "2024-03-29T15:22:28.604+01:00",
            "listIds": [444],
            "listUnsubscribed": None,
            "attributes": {"PRENOM": "David"},
        },
        {
            "email": "user_2@example.com",
            "id": 53960180,
            "emailBlacklisted": False,
            "smsBlacklisted": False,
            "createdAt": "2024-03-29T09:21:32.970+01:00",
            "modifiedAt": "2024-03-30T08:22:36.544+01:00",
            "listIds": [],
            "listUnsubscribed": [444],
            "attributes": {},
        },
        {
            "email": "user_3@example.com",
            "id": 53959637,
            "emailBlacklisted": False,
            "smsBlacklisted": False,
            "createdAt": "2024-03-28T16:01:48.905+01:00",
            "modifiedAt": "2024-03-30T08:21:14.150+01:00",
            "listIds": [444],
            "listUnsubscribed": [],
            "attributes": {},
        },
        {
            "email": "user_3@example.com",
            "id": 53035107,
            "emailBlacklisted": False,
            "smsBlacklisted": False,
            "createdAt": "2021-02-12T21:14:28.000+01:00",
            "modifiedAt": "2024-03-29T16:40:58.159+01:00",
            "listIds": [152, 233, 397, 444],
            "listUnsubscribed": [],
            "attributes": {},
        },
    ],
    "count": 4,
}


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
        self.list_contacts_url = f"{base_url}contacts/lists/{list_id}/contacts"
        self.subscribe_to_list_url = f"{self.list_contacts_url}/add"
        self.unsubscribe_from_list_url = f"{self.list_contacts_url}/remove"

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
                        "attributes": {
                            "NOM": user.last_name,
                            "PRENOM": user.first_name,
                        },
                        "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user.to_dict())
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

        brevo_user = Brevo(user.to_dict())
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
                        "attributes": {
                            "NOM": user.last_name,
                            "PRENOM": user.first_name,
                        },
                        "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user.to_dict())
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

        brevo_user = Brevo(user.to_dict())
        response = brevo_user.unsubscribe_from_commercial_list()

        self.assertEqual(json_response, response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter(self):
        """
        Test the unsubscription status of a contact from the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        json_response = {
            "email": "user@example.com",
            "id": 53960180,
            "emailBlacklisted": False,
            "smsBlacklisted": False,
            "createdAt": "2024-03-29T09:21:32.970+01:00",
            "modifiedAt": "2024-03-29T10:45:20.910+01:00",
            "attributes": {},
            "listIds": [],
            "listUnsubscribed": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
            "statistics": {},
        }
        responses.add(
            responses.GET,
            f"{self.create_contact_url}/{quote_plus(user.email)}",
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
            ],
            status=200,
            json=json_response,
        )

        brevo_user = Brevo(user.to_dict())
        response = brevo_user.has_unsubscribed_from_commercial_newsletter()

        self.assertTrue(response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_create_webhook(self):
        """
        Test the creation of a webhook.
        """
        base_url = "https://testserver.com"
        description = "Test webhook"

        json_response = {"id": "webhook-id"}
        responses.add(
            responses.POST,
            f"{settings.BREVO_API_URL}webhooks",
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
                        "type": "marketing",
                        "auth": {
                            "type": "bearer",
                            "token": settings.BREVO_WEBHOOK_TOKEN,
                        },
                        "events": ["unsubscribed"],
                        "url": "https://testserver.com/api/v1.0/newsletter-webhook/",
                        "description": description,
                        "batched": True,
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        brevo = Brevo()
        brevo.create_webhook(base_url, description)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_get_contacts_count(self):
        """
        Test the count of contacts in the commercial newsletter list.
        """
        responses.add(
            responses.GET,
            self.list_contacts_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.query_param_matcher(
                    {"limit": "1", "offset": "0", "sort": "desc"}
                ),
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
            ],
            status=200,
            json=BREVO_CONTACTS_LIST,
        )

        brevo = Brevo()
        response = brevo.get_contacts_count()

        self.assertEqual(BREVO_CONTACTS_LIST.get("count"), response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_get_contacts(self):
        """
        Test list retrieving contacts in the commercial newsletter list.
        """
        responses.add(
            responses.GET,
            self.list_contacts_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.query_param_matcher(
                    {"limit": "500", "offset": "0", "sort": "desc"}
                ),
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
            ],
            status=200,
            json=BREVO_CONTACTS_LIST,
        )

        brevo = Brevo()
        response = brevo.get_contacts()

        self.assertEqual(BREVO_CONTACTS_LIST.get("contacts"), response)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_get_contacts_limit_offset(self):
        """
        Test list retrieving contacts in the commercial newsletter list with limit and offset.
        """
        responses.add(
            responses.GET,
            self.list_contacts_url,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.query_param_matcher(
                    {"limit": "50", "offset": "50", "sort": "desc"}
                ),
                responses.matchers.header_matcher(
                    {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                    }
                ),
            ],
            status=200,
            json=BREVO_CONTACTS_LIST,
        )

        brevo = Brevo()
        response = brevo.get_contacts(limit=50, offset=50)

        self.assertEqual(BREVO_CONTACTS_LIST.get("contacts"), response)
