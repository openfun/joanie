"""Test suite for the nested batch order seats `NestedBatchOrderSeats` API"""

from http import HTTPStatus
from unittest import mock

from rest_framework.pagination import PageNumberPagination

from joanie.core import enums, factories
from joanie.core.models import OrganizationAccess
from joanie.tests.base import BaseAPITestCase


class NestedBatchOrderSeatsApiTestCase(BaseAPITestCase):
    """
    Test suite for the `NestedBatchOrderSeats` API
    """

    def test_api_nested_batch_order_seats_anonymous(self):
        """
        Anonymous user should not be able to retrieve the list of learners and
        the voucher codes.
        """
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(f"/api/v1.0/batch-orders/{batch_order.id}/seats/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_nested_batch_seats_authenticated_post_method(self):
        """
        Authenticated user should not be able to use the POST method to get the list
        of learners and the voucher codes.
        """
        owner = factories.UserFactory()
        token = self.generate_token_from_user(owner)

        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_nested_batch_seats_authenticated_patch_method(self):
        """
        Authenticated user should not be able to use the PATCH method to get the list
        of learners and the voucher codes.
        """
        owner = factories.UserFactory()
        token = self.generate_token_from_user(owner)

        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_nested_batch_seats_authenticated_put_method(self):
        """
        Authenticated user should not be able to use the PUT method to get the list
        of learners and the voucher codes.
        """
        owner = factories.UserFactory()
        token = self.generate_token_from_user(owner)

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_nested_batch_seats_authenticated_delete_method(self):
        """
        Authenticated user should not be able to use the DELETE method to get the list
        of learners and the voucher codes .
        """
        owner = factories.UserFactory()
        token = self.generate_token_from_user(owner)

        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_nested_batch_order_seats_wrong_batch_order_id(self):
        """
        Authenticated user should not be able to request the list of learners
        if the batch order id is incorrect, it should return a Bad Request (400).
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/batch-orders/fake_id/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_nested_batch_order_seats_wrong_seat_id(self):
        """
        Authenticated user should not be able to request the list of learners
        if the seat id is incorrect, it should return a Not Found error (404).
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(owner=user)

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order}/seats/wrong_id/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_nested_batch_order_seats_not_owner(self):
        """
        Authenticated user should not be able to retrieve the list of learners and
        voucher codes if they don't own the batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_nested_batch_order_seats_organization_not_related(self):
        """
        An organization that is not related to the batch order should not be able to
        retrieve the list of learners, nor the voucher codes.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_nested_batch_order_seats_authenticated_from_batch_order_owner(
        self, _mock_page_size
    ):
        """
        Authenticated user who owns the batch order should be able to retrieve the
        list of learners and their voucher codes if they aren't consumed yet.
        Also the results should be paginated.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            nb_seats=3,
        )
        # Create another batch order owned by same user
        factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            nb_seats=1,
        )
        # Create random batch orders
        factories.BatchOrderFactory.create_batch(2)
        orders = batch_order.orders.all()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 3,
                "next": f"http://testserver/api/v1.0/batch-orders/{batch_order.id}/seats/?page=2",
                "previous": None,
                "results": [
                    {
                        "id": str(orders[0].id),
                        "owner_name": None,
                        "voucher": orders[0].voucher.code,
                    },
                    {
                        "id": str(orders[1].id),
                        "owner_name": None,
                        "voucher": orders[1].voucher.code,
                    },
                ],
            },
            response.json(),
        )

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/?page=2",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 3,
                "next": None,
                "previous": (
                    f"http://testserver/api/v1.0/batch-orders/{batch_order.id}/seats/"
                ),
                "results": [
                    {
                        "id": str(orders[2].id),
                        "owner_name": None,
                        "voucher": orders[2].voucher.code,
                    },
                ],
            },
            response.json(),
        )

    def test_api_nested_batch_order_seats_authenticated_from_organization_access_user(
        self,
    ):
        """
        Authenticated user who has the right organization accesses should be able to list the
        learners of a batch order if their organization is related to it.
        """
        organization = factories.OrganizationFactory()
        for role, _ in OrganizationAccess.ROLE_CHOICES:
            with self.subTest(role=role):
                access = factories.UserOrganizationAccessFactory(
                    organization=organization,
                    role=role,
                )
                token = self.generate_token_from_user(access.user)

                batch_order = factories.BatchOrderFactory(
                    organization=organization,
                    state=enums.BATCH_ORDER_STATE_COMPLETED,
                    payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                    nb_seats=2,
                )
                # Create another batch order related to the organization
                factories.BatchOrderFactory(
                    organization=organization,
                    state=enums.BATCH_ORDER_STATE_COMPLETED,
                    payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                    nb_seats=1,
                )
                orders = batch_order.orders.all()

                response = self.client.get(
                    f"/api/v1.0/batch-orders/{batch_order.id}/seats/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )
                if role == enums.MEMBER:
                    self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)
                else:
                    self.assertStatusCodeEqual(response, HTTPStatus.OK)
                    self.assertDictEqual(
                        {
                            "count": 2,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "id": str(orders[0].id),
                                    "owner_name": None,
                                    "voucher": orders[0].voucher.code,
                                },
                                {
                                    "id": str(orders[1].id),
                                    "owner_name": None,
                                    "voucher": orders[1].voucher.code,
                                },
                            ],
                        },
                        response.json(),
                    )

    def test_api_nested_batch_order_seats_authenticated_owned_retrieve_single_seat(
        self,
    ):
        """
        Authenticated user who is the owner of the batch order should be able to
        retrieve a specific seat with the order id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            nb_seats=1,
        )

        # Simulate the learner claims his order
        learner = factories.UserFactory()
        order = batch_order.orders.first()
        order.owner = learner
        order.save()
        order.flow.update()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(order.id),
                "owner_name": learner.get_full_name(),
                "voucher": order.voucher.code,
            },
            response.json(),
        )

    def test_api_nested_batch_order_seats_authenticated_with_organization_access(self):
        """
        Authenticated user with the right permissions of organization access related
        to the batch order. Only users with the role `owner` or `admin` can access
        this data, otherwise the `member` role should not.
        """
        organization = factories.OrganizationFactory()
        for role, _ in OrganizationAccess.ROLE_CHOICES:
            with self.subTest(role=role):
                access = factories.UserOrganizationAccessFactory(
                    organization=organization,
                    role=role,
                )
                token_organization = self.generate_token_from_user(access.user)

                batch_order = factories.BatchOrderFactory(
                    organization=organization,
                    state=enums.BATCH_ORDER_STATE_COMPLETED,
                    payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                    nb_seats=1,
                )

                order = batch_order.orders.first()
                response = self.client.get(
                    f"/api/v1.0/batch-orders/{batch_order.id}/seats/{order.id}/",
                    HTTP_AUTHORIZATION=f"Bearer {token_organization}",
                )
                if role == enums.MEMBER:
                    self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)
                else:
                    self.assertStatusCodeEqual(response, HTTPStatus.OK)
                    self.assertDictEqual(
                        {
                            "id": str(order.id),
                            "owner_name": None,
                            "voucher": order.voucher.code,
                        },
                        response.json(),
                    )

    def test_api_nested_batch_order_seats_authenticated_filter_by_query(self):
        """
        It should be possible for an authenticated user to query filter by
        learner username, firstname, lastname or email a seat of a batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            nb_seats=3,
        )
        # Simulate that at least one learner claimed his seat
        order = batch_order.orders.first()
        learner = factories.UserFactory(
            username="jo_cun",
            first_name="Joanie",
            last_name="Cunningham",
            email="jo_cun@example.com",
        )
        order.owner = learner
        order.save()
        order.flow.update()
        queries = [
            "jo_cun",
            "jo_",
            "Joanie",
            "oani",
            "Cunningham",
            "nning",
            "jo_cun@example.com",
            "_cun@examp",
        ]

        for query in queries:
            with self.subTest(query=query):
                response = self.client.get(
                    f"/api/v1.0/batch-orders/{batch_order.id}/seats/?query={query}",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )
                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                content = response.json()
                self.assertEqual(content["count"], 1)
                self.assertEqual(content["results"][0]["id"], str(order.id))
