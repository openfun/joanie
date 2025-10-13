"""Test suite for the admin batch orders API create endpoint."""

from decimal import Decimal
from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminApiCreateTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API create endpoint."""

    def create_payload_batch_order(self, owner, offering, nb_seats, payment_method):
        """
        Create batch order required payload data.
        """
        return {
            "owner": owner.id if owner else None,
            "offering": offering.id if offering else None,
            "nb_seats": nb_seats,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Boulevard of dreams",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": payment_method,
            "billing_address": {
                "company_name": " Acme Corp",
                "identification_number": "456",
                "address": "Street of Hogwarts",
                "postcode": "75000",
                "country": "FR",
                "contact_name": "Jane Doe",
                "contact_email": "janedoe@example.org",
            },
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
            "signatory_firstname": "Jane",
            "signatory_lastname": "Doe",
            "signatory_profession": "General Directory",
            "signatory_email": "example2@example.org",
            "signatory_telephone": "0987654321",
        }

    def test_api_admin_batch_orders_create_anonymous(self):
        """Anonymous user should not be able to create a batch order."""

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_orders_create_not_admin_user(self):
        """Authenticated not admin user should not be able to create a batch order"""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_orders_create_fails_when_missing_company_information(self):
        """
        Authenticated admin user should not be able to create a batch order if the company's
        information are missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        offering = factories.OfferingFactory(
            product__quote_definition=factories.QuoteDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
        )
        company_keys = [
            "company_name",
            "postcode",
            "identification_number",
            "address",
            "country",
            "city",
        ]

        for company_key in company_keys:
            data = self.create_payload_batch_order(
                owner, offering, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
            )
            data[company_key] = ""

            response = self.client.post(
                "/api/v1.0/admin/batch-orders/",
                content_type="application/json",
                data=data,
            )

            self.assertEqual(
                response.status_code, HTTPStatus.BAD_REQUEST, response.json()
            )
            if company_key == "country":
                self.assertDictEqual(
                    response.json(), {company_key: ['"" is not a valid choice.']}
                )
            else:
                self.assertDictEqual(
                    response.json(), {company_key: ["This field may not be blank."]}
                )

        for company_key in company_keys:
            data = self.create_payload_batch_order(
                owner, offering, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
            )
            del data[company_key]

            response = self.client.post(
                "/api/v1.0/admin/batch-orders/",
                content_type="application/json",
                data=data,
            )

            self.assertEqual(
                response.status_code, HTTPStatus.BAD_REQUEST, response.json()
            )
            if company_key == "country":
                self.assertDictEqual(
                    response.json(), {company_key: ["This field cannot be blank."]}
                )
            else:
                self.assertDictEqual(
                    response.json(),
                    {
                        company_key: ["This field is required."],
                    },
                )

    def test_api_admin_batch_orders_create_relation_does_not_exist(self):
        """
        Authenticated admin user should not be able to create a batch order if the offering does
        not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        data = self.create_payload_batch_order(
            owner, None, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_admin_batch_orders_create_missing_owner(self):
        """
        Authenticated admin user should not be able to create a batch order if the owner is
        missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
        )
        data = self.create_payload_batch_order(
            None, offering, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_admin_batch_orders_create_offering_rule_limited_seats(self):
        """
        Authenticated admin user should not be able to create a batch order if the offering rule
        available seats does not meet the batch order number of seats requested.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=1,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(
                owner, offering, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
            ),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_admin_batch_orders_create_auto_assign_organization_with_least_orders(
        self,
    ):
        """
        Authenticated admin user should be able to create a batch order and the organization
        assigned should be the one with least active orders.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
            organizations=[organization, expected_organization],
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=4,
        )
        # Create one pending order for organization 1
        factories.OrderFactory(
            organization=organization,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_PENDING,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(
                owner, offering, 3, enums.BATCH_ORDER_WITH_CARD_PAYMENT
            ),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        batch_order = models.BatchOrder.objects.get(owner=owner)

        self.assertEqual(batch_order.organization, expected_organization)

    def test_api_admin_batch_orders_create_specify_organization(self):
        """
        Authenticated admin user should be able to create a batch order with a specified
        organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        organization1, organization2 = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
            organizations=[organization1, organization2],
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=8,
        )
        data = self.create_payload_batch_order(
            owner, offering, 3, enums.BATCH_ORDER_WITH_CARD_PAYMENT
        )
        data["organization"] = organization1.id

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        batch_order = models.BatchOrder.objects.get(owner=owner)

        self.assertEqual(batch_order.organization, organization1)

    def test_api_admin_batch_orders_create(self):
        """
        Authenticated admin user should be to create a batch order.
        Once the batch order is created, it should have a contract, a quote, and the state
        should be `quoted`. Also, the total amount should be set at 0, since freezing total
        comes afterwards.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=10,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(
                owner, offering, 2, enums.BATCH_ORDER_WITH_CARD_PAYMENT
            ),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertEqual(models.BatchOrder.objects.count(), 1)

        batch_order = models.BatchOrder.objects.get()

        self.assertEqual(batch_order.owner, owner)
        self.assertEqual(batch_order.organization, offering.organizations.first())
        self.assertEqual(batch_order.offering, offering)
        self.assertEqual(batch_order.nb_seats, 2)
        self.assertIsNotNone(batch_order.organization)
        self.assertEqual(batch_order.total, Decimal("0.00"))
        self.assertIsNotNone(batch_order.contract)
        self.assertIsNotNone(batch_order.quote)

    def test_api_admin_batch_order_create_authenticated_without_billing_address(self):
        """
        Authenticated admin user should be able to create a batch order. When they don't pass a
        specific billing address into the payload, it should use the company's address as
        the billing address.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )

        data = {
            "owner": str(factories.UserFactory().id),
            "offering": offering.id,
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
            "signatory_firstname": "Jane",
            "signatory_lastname": "Doe",
            "signatory_profession": "General Directory",
            "signatory_email": "example2@example.org",
            "signatory_telephone": "0987654321",
        }

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        batch_order = models.BatchOrder.objects.get()

        self.assertDictEqual(
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
            batch_order.billing_address,
        )
