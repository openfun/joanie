"""Test suite for the admin batch orders API export endpoint."""

from http import HTTPStatus
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import BatchOrder
from joanie.tests import format_date_export
from joanie.tests.base import BaseAPITestCase


def yes_no(value):
    """Return "Yes" if value is True, "No" otherwise."""
    return "Yes" if value else "No"


def expected_csv_content(batch_order):
    """
    Prepare the expected csv content for batch order.
    """
    content = {
        "Batch order reference": str(batch_order.id),
        "Owner": batch_order.owner.get_full_name(),
        "Email": batch_order.owner.email,
        "Company name": batch_order.company_name,
        "Company's identification number": batch_order.identification_number,
        "Company VAT registration": ""
        if not batch_order.vat_registration
        else batch_order.vat_registration,
        "Organization": batch_order.organization.title,
        "Batch Order State": batch_order.state,
        "Payment method": batch_order.payment_method,
        "Number of seats reserved": str(batch_order.nb_seats),
        "Created on": format_date_export(batch_order.created_on),
        "Updated on": format_date_export(batch_order.updated_on),
        "Product": batch_order.offering.product.title,
        "Product type": batch_order.offering.product.type,
        "Total": str(batch_order.total),
        "Quote reference": batch_order.quote.reference,
        "Organization quote signature date": format_date_export(
            batch_order.quote.organization_signed_on
        ),
        "Quote has purchase order": yes_no(batch_order.quote.has_purchase_order),
        "Contract": str(batch_order.contract.definition.title),
        "Submitted for signature": yes_no(
            batch_order.contract.signature_backend_reference
        ),
        "Buyer signature date": format_date_export(
            batch_order.contract.student_signed_on
        ),
        "Organization signature date": format_date_export(
            batch_order.contract.organization_signed_on
        ),
        "Orders generated": "",
    }

    if batch_order.payment_method == enums.BATCH_ORDER_WITH_BANK_TRANSFER:
        value = batch_order.state == enums.BATCH_ORDER_STATE_COMPLETED
        content["Submitted for signature"] = yes_no(value)

    content["Orders generated"] = yes_no(batch_order.orders.exists())

    return content


class BatchOrderAdminApiExportTestCase(BaseAPITestCase):
    """Test suite for batch order admin API csv export"""

    maxDiff = None

    def assert_response_export_csv(self, response, timestamp):
        """Convenient method to assert the response of the request"""
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="batch_orders_{timestamp.strftime("%d-%m-%Y_%H-%M-%S")}.csv"',
        )

    def test_api_admin_batch_orders_export_csv_anonymous_user(self):
        """
        Anonymous users should not be able to export orders as CSV.
        """
        response = self.client.get("/api/v1.0/admin/batch-orders/export/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_orders_export_csv_lambda_user(self):
        """
        Lambda users should not be able to export orders as CSV.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/batch-orders/export/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_orders_export_csv(self):
        """
        Authenticated admin user should be able to get the export csv of batch orders.
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

        batch_orders = BatchOrder.objects.all()

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get("/api/v1.0/admin/batch-orders/export/")

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_header = csv_content.pop(0)

        expected_headers = expected_csv_content(batch_orders[0]).keys()
        self.assertEqual(list(expected_headers), csv_header.split(","))

        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_state(self):
        """
        State filter should be applied when exporting batch orders as CSV.
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

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                "/api/v1.0/admin/batch-orders/export/"
                f"?state={enums.BATCH_ORDER_STATE_COMPLETED}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_organization(self):
        """
        Organization filter should be applied when exporting batch orders as CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [organization, another_organization] = (
            factories.OrganizationFactory.create_batch(2)
        )
        batch_orders = factories.BatchOrderFactory.create_batch(
            3, organization=organization, state=enums.BATCH_ORDER_STATE_QUOTED
        )
        factories.BatchOrderFactory.create_batch(
            2, organization=another_organization, state=enums.BATCH_ORDER_STATE_SIGNING
        )

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            # Should retrieve only batch order from organization
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?organization_ids={organization.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(organization=organization)
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

        # When combining two different organization ids (organization and another_organization)
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?organization_ids={organization.id}"
                f"&organization_ids={another_organization.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.all()
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_query(self):
        """
        Query filter should be applied when exporting batch orders CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)
        # Create another batch order that should not be found
        factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_COMPLETED)

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

        now = timezone.now()
        for query in queries:
            with self.subTest(query=query):
                with mock.patch("django.utils.timezone.now", return_value=now):
                    response = self.client.get(
                        f"/api/v1.0/admin/batch-orders/export/?query={query}"
                    )

                    self.assert_response_export_csv(response, now)

                    csv_content = response.getvalue().decode().splitlines()
                    csv_content.pop(0)

                    batch_orders = BatchOrder.objects.filter(id=batch_order.id)
                    for batch_order, csv_line in zip(
                        batch_orders, csv_content, strict=False
                    ):
                        self.assertEqual(
                            list(expected_csv_content(batch_order).values()),
                            csv_line.split(","),
                        )

    def test_api_admin_batch_orders_export_csv_filter_product_type(self):
        """
        Filter by product type should be applied when exporting batch orders CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                "/api/v1.0/admin/batch-orders/export/"
                f"?product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.all()
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_ids(self):
        """
        Filter by batch order ids should be applied when exporting batch orders CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [batch_order_1, batch_order_2] = factories.BatchOrderFactory.create_batch(
            2, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory.create_batch(10)

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?ids={batch_order_1.id}"
                f"&ids={batch_order_2.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            id__in=[batch_order_1.id, batch_order_2.id]
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_product_ids(self):
        """
        Filter by product ids should be applied when exporting batch orders CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        batch_orders = factories.BatchOrderFactory.create_batch(
            3, offering=offering, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory.create_batch(5)

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?product_ids={offering.product.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(relation__product=offering.product)
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_orders_export_csv_filter_course_ids(self):
        """
        Filter by course ids should be applied when exporting batch orders CSV.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        offering_2 = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        batch_order = factories.BatchOrderFactory.create_batch(
            2, offering=offering, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )
        factories.BatchOrderFactory(
            offering=offering_2, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )

        factories.BatchOrderFactory.create_batch(5)

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?course_ids={offering.course.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(relation__course=offering.course)
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

        # We can combine course ids
        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/export/?course_ids={offering.course.id}"
                f"&course_ids={offering_2.course.id}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            relation__course_id__in=[offering.course.id, offering_2.course.id]
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

    def test_api_admin_batch_order_export_csv_filter_payment_method(self):
        """
        Payment method filter should be applied to export csv of batch orders.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_CARD_PAYMENT,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                "/api/v1.0/admin/batch-orders/export/"
                f"?payment_method={enums.BATCH_ORDER_WITH_BANK_TRANSFER}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                "/api/v1.0/admin/batch-orders/export/"
                f"?payment_method={enums.BATCH_ORDER_WITH_CARD_PAYMENT}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            payment_method=enums.BATCH_ORDER_WITH_CARD_PAYMENT
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get(
                "/api/v1.0/admin/batch-orders/export/"
                f"?payment_method={enums.BATCH_ORDER_WITH_PURCHASE_ORDER}"
            )

        self.assert_response_export_csv(response, now)

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        batch_orders = BatchOrder.objects.filter(
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER
        )
        for batch_order, csv_line in zip(batch_orders, csv_content, strict=False):
            self.assertEqual(
                list(expected_csv_content(batch_order).values()),
                csv_line.split(","),
            )
