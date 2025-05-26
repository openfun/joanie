"""Test suite for the admin batch orders API create endpoint."""

from decimal import Decimal as D
from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories, models


class BatchOrdersAdminApiCreateTestCase(TestCase):
    """Test suite for the admin batch orders API create endpoint."""

    def create_payload_batch_order(self, owner, relation, nb_seats):
        """
        Create batch order required payload data.
        """
        return {
            "owner": owner.id if owner else None,
            "relation": relation.id if relation else None,
            "nb_seats": nb_seats,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Boulevard of dreams",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": factories.TraineeFactory.create_batch(nb_seats),
        }

    def test_api_admin_batch_orders_create_anonymous(self):
        """Anonymous user should not be able to create a batch order."""

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_create_not_admin_user(self):
        """Authenticated not admin user should not be able to create a batch order"""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_create_number_of_seats_does_not_match_trainees(
        self,
    ):
        """
        Authenticated admin user should not be able to create a batch order if the number
        of seats is not equal to the number of trainees declared.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )

        data = self.create_payload_batch_order(owner, relation, 2)
        data.update(nb_seats=1)

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_admin_batch_orders_create_fails_when_missing_company_information(self):
        """
        Authenticated admin user should not be able to create a batch order if the company's
        information are missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
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
            data = self.create_payload_batch_order(owner, relation, 2)
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
            data = self.create_payload_batch_order(owner, relation, 2)
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
        Authenticated admin user should not be able to create a batch order if the relation does
        not exist.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        data = self.create_payload_batch_order(owner, None, 2)

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_admin_batch_orders_create_missing_owner(self):
        """
        Authenticated admin user should not be able to create a batch order if the owner is
        missing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        data = self.create_payload_batch_order(None, relation, 2)

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_admin_batch_orders_create_order_group_limited_seats(self):
        """
        Authenticated admin user should not be able to create a batch order if the order group
        available seats does not meet the batch order number of seats requested.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        factories.OrderGroupFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=1,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(owner, relation, 2),
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_admin_batch_orders_create_when_order_group_has_discount(self):
        """
        Authenticated user should be able to get the discounted price on the batch order when
        there is a discount on the order group.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        order_group = factories.OrderGroupFactory(
            discount=factories.DiscountFactory(rate=0.1),
            course_product_relation=relation,
            is_active=True,
            nb_seats=4,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(owner, relation, 4),
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        batch_order = models.BatchOrder.objects.get(owner=owner)

        self.assertEqual(batch_order.relation, relation)
        self.assertEqual(batch_order.nb_seats, 4)
        self.assertEqual(batch_order.order_groups.first(), order_group)
        self.assertEqual(batch_order.total, D("36.00"))

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
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
            organizations=[organization, expected_organization],
        )
        factories.OrderGroupFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=4,
        )
        # Create one pending order for organization 1
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(owner, relation, 3),
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

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
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
            organizations=[organization1, organization2],
        )
        factories.OrderGroupFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=8,
        )
        data = self.create_payload_batch_order(owner, relation, 3)
        data["organization"] = organization1.id

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        batch_order = models.BatchOrder.objects.get(owner=owner)

        self.assertEqual(batch_order.organization, organization1)

    def test_api_admin_batch_orders_create_with_voucher_code(self):
        """
        Authenticated admin user should be able to create a batch order with a voucher code.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=123,
        )
        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.5),
            multiple_use=False,
            multiple_users=False,
        )

        data = self.create_payload_batch_order(owner, relation, 2)
        data["voucher"] = voucher.code

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=data,
        )

        batch_order = models.BatchOrder.objects.get(owner=owner)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        self.assertEqual(batch_order.total, D("123.00"))

    def test_api_admin_batch_orders_create(self):
        """Authenticated admin user should be to create a batch order."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        owner = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        factories.OrderGroupFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=10,
        )

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/",
            content_type="application/json",
            data=self.create_payload_batch_order(owner, relation, 2),
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        self.assertEqual(models.BatchOrder.objects.count(), 1)
