"""Test suite for BatchOrder Create API"""

from decimal import Decimal
from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class BatchOrderCreateAPITest(BaseAPITestCase):
    """Tests for BatchOrder Create API"""

    def test_api_batch_order_create_anonymous(self):
        """Anonymous user shouldn't be able to create a batch order"""

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_batch_order_create_fails_when_missing_company_informations(self):
        """
        Authenticated user shouldn't be able to create a batch order if the company's informations
        are missing in the payload.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=456,
        )

        data = {
            "offering_id": offering.id,
            "nb_seats": 2,
            "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
            "vat_registration": "987654321",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())
        self.assertEqual(
            response.json(),
            {
                "company_name": ["This field is required."],
                "identification_number": ["This field is required."],
                "address": ["This field is required."],
                "postcode": ["This field is required."],
                "city": ["This field is required."],
            },
        )

    def test_api_batch_order_create_authenticated(self):
        """
        Authenticated user should be able to create a batch order with the required
        data in the payload. The user who request is the owner of the batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
            product__price=10,
        )

        data = {
            "offering_id": offering.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            "organization_id": offering.organizations.first().id,
            "billing_address": {
                "company_name": " Acme Corp",
                "identification_number": "456",
                "address": "Street of Hogwarts",
                "postcode": "75000",
                "country": "FR",
                "contact_email": "jane@example.org",
                "contact_name": "Jane Doe",
            },
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        batch_order = models.BatchOrder.objects.get(owner=user)

        self.assertEqual(batch_order.owner, user)
        self.assertEqual(batch_order.offering, offering)
        self.assertEqual(batch_order.nb_seats, 2)
        self.assertEqual(batch_order.company_name, data["company_name"])
        self.assertIsNotNone(batch_order.organization)
        self.assertEqual(batch_order.total, Decimal("0.00"))

    def test_api_batch_order_create_authenticated_without_billing_address(self):
        """
        Authenticated user should be able to create a batch order. When they don't pass a
        specific billing address into the payload, it should use the company's address as
        the billing address.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )

        data = {
            "offering_id": offering.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            "organization_id": offering.organizations.first().id,
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        batch_order = models.BatchOrder.objects.get()

        self.assertDictEqual(
            batch_order.billing_address,
            {
                "company_name": batch_order.company_name,
                "identification_number": batch_order.identification_number,
                "address": batch_order.address,
                "city": batch_order.city,
                "postcode": batch_order.postcode,
                "country": batch_order.country.code,
                "contact_email": batch_order.administrative_email,
                "contact_name": (
                    f"{batch_order.administrative_firstname} {batch_order.administrative_lastname}"
                ),
            },
        )

    def test_api_batch_order_create_authenticated_fails_offering_rule_no_more_seats_available(
        self,
    ):
        """
        Authenticated user should not be able to create a batch order when the requested number
        of seats is above the offering rule available seats.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=1,
        )

        data = {
            "offering_id": offering.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": enums.BATCH_ORDER_WITH_BANK_TRANSFER,
            "billing_address": {
                "company_name": " Acme Corp",
                "identification_number": "456",
                "address": "Street of Hogwarts",
                "postcode": "75000",
                "country": "FR",
                "contact_email": "jane@example.org",
                "contact_name": "Jane Doe",
            },
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())
        self.assertEqual(
            response.json(),
            {
                "offering_rule": [
                    "Maximum number of orders reached for "
                    f"product {offering.product.title}"
                ]
            },
        )

    def test_api_batch_order_create_relation_does_not_exist(self):
        """
        Authenticated user passing a offering id that does not exist should get an error and
        the batch order should not be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        data = {
            "offering_id": "fake_relation_id",
            "nb_seats": 1,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_batch_order_create_auto_assign_organization_with_least_orders(self):
        """
        The order auto-assignment logic should always return the organization with the least
        active orders count for the given product course offering when we create a batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )
        offering = factories.OfferingFactory(
            organizations=[organization, expected_organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )

        ignored_states = [
            state
            for [state, _] in enums.ORDER_STATE_CHOICES
            if state not in enums.ORDER_STATES_BINDING
        ]

        # Create orders for the first organization (1 for each ignored, 1 take in account)
        for state in ignored_states:
            factories.OrderFactory(
                organization=organization,
                product=offering.product,
                course=offering.course,
                state=state,
            )
        factories.OrderFactory(
            organization=organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_PENDING,
        )

        # ignored orders for the second organization
        for state in ignored_states:
            factories.OrderFactory(
                organization=expected_organization,
                product=offering.product,
                course=offering.course,
                state=state,
            )

        data = {
            "offering_id": offering.id,
            "nb_seats": 1,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            "billing_address": {
                "company_name": " Acme Corp",
                "identification_number": "456",
                "address": "Street of Hogwarts",
                "postcode": "75000",
                "country": "FR",
                "contact_email": "janedoe@example.org",
                "contact_name": "Jane Doe",
            },
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        batch_order = models.BatchOrder.objects.get(relation=offering)

        self.assertEqual(batch_order.organization, expected_organization)
