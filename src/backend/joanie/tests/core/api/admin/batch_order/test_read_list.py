"""Test suite for the admin batch orders API list endpoint."""

from http import HTTPStatus

from django.conf import settings

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminApiListTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API list endpoint."""

    def test_api_admin_list_batch_orders_anonymous(self):
        """Anonymous user should not be able to list the batch orders"""
        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_list_batch_orders_authenticated_user(self):
        """Authenticated user should not be able to list batch orders"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_list_batch_orders_authenticated_admin(self):
        """Authenticated admin user should be able to list batch orders"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_orders = factories.BatchOrderFactory.create_batch(
            3,
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        expected_return = [
            {
                "id": str(batch_order.id),
                "address": batch_order.address,
                "city": batch_order.city,
                "company_name": batch_order.company_name,
                "contract": {
                    "definition_title": batch_order.contract.definition.title,
                    "id": str(batch_order.contract.id),
                    "organization_signed_on": None,
                    "student_signed_on": None,
                    "submitted_for_signature_on": None,
                },
                "country": batch_order.country.code,
                "currency": settings.DEFAULT_CURRENCY,
                "identification_number": batch_order.identification_number,
                "main_invoice_reference": None,
                "nb_seats": batch_order.nb_seats,
                "organization": {
                    "code": batch_order.organization.code,
                    "id": str(batch_order.organization.id),
                    "title": batch_order.organization.title,
                },
                "owner": str(batch_order.owner.id),
                "postcode": batch_order.postcode,
                "offering": str(batch_order.offering.id),
                "total": float(batch_order.total),
                "vouchers": [],
                "offering_rules": [],
                "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                "billing_address": {
                    "company_name": batch_order.company_name,
                    "identification_number": batch_order.identification_number,
                    "address": batch_order.address,
                    "postcode": batch_order.postcode,
                    "country": batch_order.billing_address["country"],
                    "contact_email": "janedoe@example.org",
                    "contact_name": "Jane Doe",
                },
                "vat_registration": None,
                "administrative_email": None,
                "administrative_firstname": None,
                "administrative_lastname": None,
                "administrative_telephone": None,
                "administrative_profession": None,
                "signatory_email": None,
                "signatory_firstname": None,
                "signatory_lastname": None,
                "signatory_telephone": None,
                "signatory_profession": None,
                "quote": {
                    "definition_title": batch_order.quote.definition.title,
                    "has_purchase_order": False,
                    "id": str(batch_order.quote.id),
                    "organization_signed_on": None,
                },
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
                "contract_submitted": False,
            }
            for batch_order in batch_orders
        ]

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(expected_return, response.json()["results"])

    def test_api_admin_list_batch_orders_filter_state(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by state.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            if state in [
                enums.BATCH_ORDER_STATE_DRAFT,
                enums.BATCH_ORDER_STATE_CANCELED,
            ]:
                continue
            factories.BatchOrderFactory(state=state)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?state={enums.BATCH_ORDER_STATE_COMPLETED}",
        )

        content = response.json()
        batch_order = models.BatchOrder.objects.get(
            state=enums.BATCH_ORDER_STATE_COMPLETED
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order.id))

    def test_api_admin_list_batch_orders_filter_organization(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [organization, another_organization] = (
            factories.OrganizationFactory.create_batch(2)
        )
        batch_order = factories.BatchOrderFactory(
            organization=organization, state=enums.BATCH_ORDER_STATE_QUOTED
        )
        factories.BatchOrderFactory.create_batch(
            2, organization=another_organization, state=enums.BATCH_ORDER_STATE_SIGNING
        )
        factories.BatchOrderFactory.create_batch(3)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?organization_ids={organization.id}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order.id))

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?organization_ids={another_organization.id}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 2)

    def test_api_admin_list_batch_orders_filter_query(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by query.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)

        queries = [
            # Check course queries
            batch_order.offering.course.code,
            batch_order.offering.course.title,
            # Check product queries
            batch_order.offering.product.title,
            # Check organization queries
            batch_order.organization.title,
            batch_order.organization.code,
            # Check owner queries
            batch_order.owner.email,
            batch_order.owner.username,
            # Check with company name
            batch_order.company_name,
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/?query={query}",
            )

            content = response.json()

            self.assertStatusCodeEqual(response, HTTPStatus.OK)
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(batch_order.id))

    def test_api_admin_list_batch_orders_product_type(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by product type.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order.id))

    def test_api_admin_list_batch_orders_filter_ids(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by ids.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [batch_order_1, batch_order_2] = factories.BatchOrderFactory.create_batch(
            2, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory.create_batch(5)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?ids={batch_order_1.id}"
        )
        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order_1.id))

        # We can combine ids in the filter
        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?ids={batch_order_1.id}&ids={batch_order_2.id}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 2)

    def test_api_admin_list_batch_orders_filter_product_ids(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by product ids.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        factories.BatchOrderFactory.create_batch(
            3, offering=offering, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory.create_batch(5)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?product_ids={offering.product.id}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 3)

    def test_api_admin_list_batch_orders_filter_course_ids(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by course ids.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        factories.BatchOrderFactory(
            offering=offering, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory.create_batch(3)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?course_ids={offering.course.id}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)

    def test_api_admin_list_batch_orders_filter_payment_method(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by payment method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order_bank_transfer = factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        batch_order_card_payment = factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_CARD_PAYMENT,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        batch_order_purchase_order = factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?payment_method={enums.BATCH_ORDER_WITH_BANK_TRANSFER}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order_bank_transfer.id))

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?payment_method={enums.BATCH_ORDER_WITH_CARD_PAYMENT}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order_card_payment.id))

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?payment_method={enums.BATCH_ORDER_WITH_PURCHASE_ORDER}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(
            content["results"][0]["id"], str(batch_order_purchase_order.id)
        )
