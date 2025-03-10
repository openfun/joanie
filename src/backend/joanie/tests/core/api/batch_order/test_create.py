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

    def test_api_batch_order_create_fails_number_seats_does_not_match_trainees(self):
        """
        Authenticated user shouldn't be able to create a batch order if the number of
        seats is not equal to number of trainees declared in the payload.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=123,
        )

        data = {
            "relation_id": relation.id,
            "nb_seats": 3,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
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
            {"__all__": ["The number of trainees must match the number of seats."]},
        )

    def test_api_batch_order_create_fails_when_missing_company_informations(self):
        """
        Authenticated user shouldn't be able to create a batch order if the company's informations
        are missing in the payload.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=456,
        )

        data = {
            "relation_id": relation.id,
            "nb_seats": 2,
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
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
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )

        data = {
            "relation_id": relation.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
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
        self.assertEqual(batch_order.relation, relation)
        self.assertEqual(batch_order.nb_seats, 2)
        self.assertEqual(batch_order.trainees, data["trainees"])
        self.assertEqual(batch_order.company_name, data["company_name"])
        self.assertIsNotNone(batch_order.organization)
        self.assertEqual(batch_order.total, Decimal("20.00"))

    def test_api_batch_order_create_authenticated_with_voucher_code(self):
        """
        Authenticated user should be able to create a batch order and use a voucher code to
        have a reduction on the total price.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=100,
        )
        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.2),
            multiple_use=False,
            multiple_users=False,
        )

        data = {
            "relation_id": relation.id,
            "nb_seats": 3,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "voucher": voucher.code,
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
                {"first_name": "Joanie", "last_name": "Gioani"},
            ],
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
        self.assertEqual(batch_order.relation, relation)
        self.assertEqual(batch_order.nb_seats, 3)
        self.assertEqual(batch_order.trainees, data["trainees"])
        self.assertEqual(batch_order.company_name, data["company_name"])
        self.assertIsNotNone(batch_order.organization)
        self.assertEqual(batch_order.total, Decimal("240.00"))

    def test_api_batch_order_create_authenticated_fails_order_group_no_more_seats_available(
        self,
    ):
        """
        Authenticated user should not be able to create a batch order when the requested number
        of seats is above the order group available seats.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=10,
        )
        factories.OrderGroupFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=1,
        )

        data = {
            "relation_id": relation.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
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
                "order_group": [
                    "Maximum number of orders reached for "
                    f"product {relation.product.title}"
                ]
            },
        )

    def test_api_batch_order_create_relation_does_not_exist(self):
        """
        Authenticated user passing a relation id that does not exist should get an error and
        the batch order should not be created.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        data = {
            "relation_id": "fake_relation_id",
            "nb_seats": 1,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
            ],
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_batch_order_create_authenticated_when_order_group_for_relation_has_discount(
        self,
    ):
        """
        When the order group has a discount and enough available seats, the batch order
        should be created with the discounted price.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
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
        data = {
            "relation_id": relation.id,
            "nb_seats": 3,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
                {"first_name": "Joanie", "last_name": "Richie"},
            ],
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
        self.assertEqual(batch_order.relation, relation)
        self.assertEqual(batch_order.nb_seats, 3)
        self.assertEqual(batch_order.order_groups.first(), order_group)
        self.assertEqual(batch_order.total, Decimal("27.00"))

    def test_api_batch_order_create_auto_assign_organization_with_least_orders(self):
        """
        The order auto-assignment logic should always return the organization with the least
        active orders count for the given product course relation when we create a batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization, expected_organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
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
                product=relation.product,
                course=relation.course,
                state=state,
            )
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )

        # ignored orders for the second organization
        for state in ignored_states:
            factories.OrderFactory(
                organization=expected_organization,
                product=relation.product,
                course=relation.course,
                state=state,
            )

        data = {
            "relation_id": relation.id,
            "nb_seats": 1,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "trainees": [
                {"first_name": "John", "last_name": "Doe"},
            ],
        }

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        batch_order = models.BatchOrder.objects.get(relation=relation)

        self.assertEqual(batch_order.organization, expected_organization)
