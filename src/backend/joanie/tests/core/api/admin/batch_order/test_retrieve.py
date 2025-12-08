"""Test suite for the admin batch orders API read detail endpoint."""

from decimal import Decimal
from http import HTTPStatus
from unittest import mock

from django.conf import settings

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.core.utils import get_default_currency_symbol
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
                            "call_to_action": batch_order.offering.course.state[
                                "call_to_action"
                            ],
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
                            batch_order.offering.product.contract_definition_batch_order.id
                        ),
                        "quote_definition": str(
                            batch_order.offering.product.quote_definition.id
                        ),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in (
                                batch_order.offering.product.target_courses.all().order_by(
                                    "product_target_relations__position"
                                )
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
                    "city": batch_order.billing_address["city"],
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
                "state": batch_order.state,
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
                "contract_submitted": False,
                "orders": [],
                "available_actions": {
                    "confirm_quote": True,
                    "confirm_purchase_order": False,
                    "confirm_bank_transfer": False,
                    "submit_for_signature": False,
                    "generate_orders": False,
                    "cancel": True,
                    "next_action": "confirm_quote",
                },
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
        batch_order.refresh_from_db()
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
                            "call_to_action": batch_order.offering.course.state[
                                "call_to_action"
                            ],
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
                            batch_order.offering.product.contract_definition_batch_order.id
                        ),
                        "quote_definition": str(
                            batch_order.offering.product.quote_definition.id
                        ),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in (
                                batch_order.offering.product.target_courses.all().order_by(
                                    "product_target_relations__position"
                                )
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
                    "city": batch_order.billing_address["city"],
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
                "state": batch_order.state,
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
                "contract_submitted": False,
                "orders": [],
                "available_actions": {
                    "confirm_quote": False,
                    "confirm_purchase_order": False,
                    "confirm_bank_transfer": False,
                    "submit_for_signature": True,
                    "generate_orders": False,
                    "cancel": True,
                    "next_action": "submit_for_signature",
                },
            },
            response.json(),
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_admin_batch_order_read_with_orders(self, _mock_thumbnail):
        """Admin user should be able to get the detail of a batch order with orders"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
            nb_seats=1,
        )

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/{batch_order.id}/"
            )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(batch_order.id),
                "created_on": format_date(batch_order.created_on),
                "updated_on": format_date(batch_order.updated_on),
                "address": batch_order.address,
                "city": batch_order.city,
                "company_name": batch_order.company_name,
                "contract": {
                    "definition_title": batch_order.contract.definition.title,
                    "id": str(batch_order.contract.id),
                    "organization_signed_on": format_date(
                        batch_order.contract.organization_signed_on
                    ),
                    "student_signed_on": format_date(
                        batch_order.contract.student_signed_on
                    ),
                    "submitted_for_signature_on": format_date(
                        batch_order.contract.submitted_for_signature_on
                    ),
                },
                "contract_submitted": True,
                "country": batch_order.country.code,
                "currency": settings.DEFAULT_CURRENCY,
                "identification_number": batch_order.identification_number,
                "main_invoice_reference": batch_order.main_invoice.reference,
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
                            "datetime": format_date(
                                batch_order.offering.course.state["datetime"]
                            ),
                            "call_to_action": batch_order.offering.course.state[
                                "call_to_action"
                            ],
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
                            batch_order.offering.product.contract_definition_batch_order.id
                        ),
                        "quote_definition": str(
                            batch_order.offering.product.quote_definition.id
                        ),
                        "target_courses": [
                            str(target_course.id)
                            for target_course in (
                                batch_order.offering.product.target_courses.all().order_by(
                                    "product_target_relations__position"
                                )
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
                    "city": batch_order.billing_address["city"],
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
                "state": batch_order.state,
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
                "orders": [
                    {
                        "batch_order": str(batch_order.id),
                        "course_code": order.course.code if order.course else None,
                        "created_on": format_date(order.created_on),
                        "updated_on": format_date(order.updated_on),
                        "enrollment_id": str(order.enrollment.id)
                        if order.enrollment
                        else None,
                        "id": str(order.id),
                        "organization_title": order.organization.title,
                        "owner_name": None,
                        "product_title": order.product.title,
                        "state": order.state,
                        "total": float(order.total),
                        "total_currency": get_default_currency_symbol(),
                        "discount": str(order.voucher.discount)
                        if order.voucher
                        else None,
                        "voucher": order.voucher.code if order.voucher else None,
                    }
                    for order in batch_order.orders.all()
                ],
                "available_actions": {
                    "confirm_quote": False,
                    "confirm_purchase_order": False,
                    "confirm_bank_transfer": False,
                    "submit_for_signature": False,
                    "generate_orders": False,
                    "cancel": True,
                    "next_action": None,
                },
            },
            response.json(),
        )
