"""Test suite for the admin batch orders API read detail endpoint."""

from decimal import Decimal
from http import HTTPStatus
from unittest import mock

from django.conf import settings

from joanie.core import enums, factories
from joanie.core.serializers import fields
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
                "offering": {
                    "id": str(batch_order.offering.id),
                    "uri": batch_order.offering.uri,
                    "can_edit": batch_order.offering.can_edit,
                    "course": {
                        "code": batch_order.offering.course.code,
                        "id": str(batch_order.offering.course.id),
                        "title": batch_order.offering.course.title,
                        "state": {
                            "priority": batch_order.offering.course.state["priority"],
                            "datetime": batch_order.offering.course.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z")
                            if batch_order.offering.course.state["datetime"]
                            else None,
                            "call_to_action": batch_order.offering.course.state["call_to_action"],
                            "text": batch_order.offering.course.state["text"],
                        },
                    },
                    "offering_rules": [],
                    "product": {
                        "price": float(batch_order.offering.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(batch_order.offering.product.id),
                        "title": batch_order.offering.product.title,
                        "description": batch_order.offering.product.description,
                        "call_to_action": batch_order.offering.product.call_to_action,
                        "type": batch_order.offering.product.type,
                        "certificate_definition": str(
                            batch_order.offering.product.certificate_definition.id
                        ),
                        "contract_definition_order": None,
                        "contract_definition_batch_order": str(batch_order.offering.product.contract_definition_batch_order.id),
                        "quote_definition": str(batch_order.offering.product.quote_definition.id),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in batch_order.offering.product.target_courses.all().order_by(
                                "product_target_relations__position"
                            )
                        ],
                    },
                    "organizations": [
                        {
                            "code": organization.code,
                            "id": str(organization.id),
                            "title": organization.title,
                        }
                        for organization in batch_order.offering.organizations.all().order_by(
                            "created_on"
                        )
                    ],
                },
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
                "orders": [],
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
                "offering": {
                    "id": str(batch_order.offering.id),
                    "uri": batch_order.offering.uri,
                    "can_edit": batch_order.offering.can_edit,
                    "course": {
                        "code": batch_order.offering.course.code,
                        "id": str(batch_order.offering.course.id),
                        "title": batch_order.offering.course.title,
                        "state": {
                            "priority": batch_order.offering.course.state["priority"],
                            "datetime": batch_order.offering.course.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z")
                            if batch_order.offering.course.state["datetime"]
                            else None,
                            "call_to_action": batch_order.offering.course.state["call_to_action"],
                            "text": batch_order.offering.course.state["text"],
                        },
                    },
                    "offering_rules": [],
                    "product": {
                        "price": float(batch_order.offering.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(batch_order.offering.product.id),
                        "title": batch_order.offering.product.title,
                        "description": batch_order.offering.product.description,
                        "call_to_action": batch_order.offering.product.call_to_action,
                        "type": batch_order.offering.product.type,
                        "certificate_definition": str(
                            batch_order.offering.product.certificate_definition.id
                        ),
                        "contract_definition_order": None,
                        "contract_definition_batch_order": str(
                            batch_order.offering.product.contract_definition_batch_order.id),
                        "quote_definition": str(batch_order.offering.product.quote_definition.id),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in batch_order.offering.product.target_courses.all().order_by(
                                "product_target_relations__position"
                            )
                        ],
                    },
                    "organizations": [
                        {
                            "code": organization.code,
                            "id": str(organization.id),
                            "title": organization.title,
                        }
                        for organization in batch_order.offering.organizations.all().order_by(
                            "created_on"
                        )
                    ],
                },
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
                "orders": [],
            },
            response.json(),
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_admin_batch_order_read_with_orders(self, _mock_thumbnail):
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
            nb_seats=1,
        )

        with self.record_performance():
            response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        organization_address = batch_order.organization.addresses.filter(is_main=True).first()
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
                "offering": {
                    "id": str(batch_order.offering.id),
                    "uri": batch_order.offering.uri,
                    "can_edit": batch_order.offering.can_edit,
                    "course": {
                        "code": batch_order.offering.course.code,
                        "id": str(batch_order.offering.course.id),
                        "title": batch_order.offering.course.title,
                        "state": {
                            "priority": batch_order.offering.course.state["priority"],
                            "datetime": format_date(batch_order.offering.course.state["datetime"]),
                            "call_to_action": batch_order.offering.course.state["call_to_action"],
                            "text": batch_order.offering.course.state["text"],
                        },
                    },
                    "offering_rules": [],
                    "product": {
                        "price": float(batch_order.offering.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(batch_order.offering.product.id),
                        "title": batch_order.offering.product.title,
                        "description": batch_order.offering.product.description,
                        "call_to_action": batch_order.offering.product.call_to_action,
                        "type": batch_order.offering.product.type,
                        "certificate_definition": str(
                            batch_order.offering.product.certificate_definition.id
                        ),
                        "contract_definition_order": None,
                        "contract_definition_batch_order": str(batch_order.offering.product.contract_definition_batch_order.id),
                        "quote_definition": str(batch_order.offering.product.quote_definition.id),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in batch_order.offering.product.target_courses.all().order_by(
                                "product_target_relations__position"
                            )
                        ],
                    },
                    "organizations": [
                        {
                            "code": organization.code,
                            "id": str(organization.id),
                            "title": organization.title,
                        }
                        for organization in batch_order.offering.organizations.all().order_by(
                            "created_on"
                        )
                    ],
                },
                "total": float(batch_order.total),
                "vouchers": batch_order.vouchers,
                "offering_rules": [],
                "payment_method": enums.BATCH_ORDER_WITH_BANK_TRANSFER,
                "quote": {
                    "definition_title": batch_order.quote.definition.title,
                    "has_purchase_order": False,
                    "id": str(batch_order.quote.id),
                    "organization_signed_on": format_date(batch_order.quote.organization_signed_on),
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
                "orders": [
                    {
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": batch_order.offering.course.code,
                            "id": str(batch_order.offering.course.id),
                            "title": batch_order.offering.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": format_date(order.created_on),
                        "credit_card_id": None,
                        "enrollment": None,
                        "id": str(order.id),
                        "main_invoice_reference": None,
                        "offering_rule_ids": [],
                        "payment_schedule": [],
                        "has_waived_withdrawal_right": order.has_waived_withdrawal_right,
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
                        "owner": None,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "from_batch_order": False,
                        "target_courses": [],
                        "target_enrollments": [],
                        "total": float(batch_order.offering.product.price),
                        "total_currency": settings.DEFAULT_CURRENCY,
                    }
                    for order in batch_order.orders.all()
                ],
            },
            response.json(),
        )
