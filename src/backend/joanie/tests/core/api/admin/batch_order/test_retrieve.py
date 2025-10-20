"""Test suite for the admin batch orders API read detail endpoint."""

from decimal import Decimal
from http import HTTPStatus

from django.conf import settings

from joanie.core import enums, factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminApiDetailTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API read detail endpoint."""

    maxDiff = None

    def test_api_admin_batch_order_read_anonymous(self):
        """Anonymous user should not be able to read detail of a batch order"""
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_order_read_authenticated(self):
        """Authenticated user should not be able to read the detail of a batch order"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_order_read_admin_authenticated(self):
        """Authenticated admin user should be able to read the detail of a batch order"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(batch_order.id),
                "created_on": format_date(batch_order.created_on),
                "updated_on": format_date(batch_order.updated_on),
                "address": batch_order.address,
                "city": batch_order.city,
                "company_name": batch_order.company_name,
                "contract_id": str(batch_order.contract.id),
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
                "owner": {
                    "id": str(batch_order.owner.id),
                    "email": batch_order.owner.email,
                    "full_name": batch_order.owner.get_full_name(),
                    "username": batch_order.owner.username,
                },
                "postcode": batch_order.postcode,
                "offering": str(batch_order.offering.id),
                "total": float(batch_order.total),
                "vouchers": [],
                "offering_rules": [],
                "payment_method": enums.BATCH_ORDER_WITH_BANK_TRANSFER,
                "quote": {
                    "definition_title": batch_order.quote.definition.title,
                    "has_purchase_order": False,
                    "id": str(batch_order.quote.id),
                    "organization_signed_on": None,
                },
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
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
            },
            response.json(),
        )

    def test_api_admin_batch_order_read_with_quote(self):
        """
        Admin user should be able to get the detail of a batch order with a quote
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )
        batch_order.freeze_total(Decimal("100.00"))

        response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(batch_order.id),
                "created_on": format_date(batch_order.created_on),
                "updated_on": format_date(batch_order.updated_on),
                "address": batch_order.address,
                "city": batch_order.city,
                "company_name": batch_order.company_name,
                "contract_id": str(batch_order.contract.id),
                "country": batch_order.country.code,
                "currency": settings.DEFAULT_CURRENCY,
                "identification_number": batch_order.identification_number,
                "main_invoice_reference": str(batch_order.main_invoice.reference),
                "nb_seats": batch_order.nb_seats,
                "organization": {
                    "code": batch_order.organization.code,
                    "id": str(batch_order.organization.id),
                    "title": batch_order.organization.title,
                },
                "owner": {
                    "id": str(batch_order.owner.id),
                    "email": batch_order.owner.email,
                    "full_name": batch_order.owner.get_full_name(),
                    "username": batch_order.owner.username,
                },
                "postcode": batch_order.postcode,
                "offering": str(batch_order.offering.id),
                "total": float(batch_order.total),
                "vouchers": [],
                "offering_rules": [],
                "payment_method": enums.BATCH_ORDER_WITH_BANK_TRANSFER,
                "quote": {
                    "definition_title": batch_order.quote.definition.title,
                    "has_purchase_order": False,
                    "id": str(batch_order.quote.id),
                    "organization_signed_on": format_date(
                        batch_order.quote.organization_signed_on
                    ),
                },
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
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
            },
            response.json(),
        )
