"""Tests for the Order API."""
import datetime
import json
import logging
import random
import uuid

from django.test import override_settings
from django.utils import timezone

from joanie.core import enums, factories, models

from .base import BaseAPITestCase


class OrderApiTest(BaseAPITestCase):
    """Test the API of the Order object."""

    def test_api_order_read_list_anonymous(self):
        """It should not be possible to retrieve the list of orders for anonymous users."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        factories.OrderFactory(product=product)

        response = self.client.get(
            "/api/orders/",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)

        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_read_list_authenticated(self):
        """Authenticated users retrieving the list of orders should only see theirs."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order, other_order = factories.OrderFactory.create_batch(2, product=product)

        # The owner can see his/her order
        token = self.get_user_token(order.owner.username)

        response = self.client.get(
            "/api/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "id": str(order.uid),
                        "owner": order.owner.username,
                        "price": str(product.price),
                        "product": str(order.product.uid),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

        # The owner of the other order can only see his/her order
        token = self.get_user_token(other_order.owner.username)

        response = self.client.get(
            "/api/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(other_order.uid),
                        "course": other_order.course.code,
                        "created_on": other_order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "owner": other_order.owner.username,
                        "price": str(other_order.price),
                        "product": str(other_order.product.uid),
                        "state": other_order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_detail_anonymous(self):
        """Anonymous users should not be allowed to retrieve an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.get("/api/orders/{!s}/".format(order.uid))
        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

    def test_api_order_read_detail_authenticated_owner(self):
        """Authenticated users should be allowed to retrieve an order they own."""
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product, owner=owner)
        token = self.get_user_token(owner.username)

        response = self.client.get(
            "/api/orders/{!s}/".format(order.uid),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "course": order.course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": order.state,
                "owner": owner.username,
                "price": str(product.price),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
            },
        )

    def test_api_order_read_detail_authenticated_not_owner(self):
        """Authenticated users should not be able to retrieve an order they don't own."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token("panoramix")

        response = self.client.get(
            "/api/orders/{!s}/".format(order.uid),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

    def test_api_order_create_anonymous(self):
        """Anonymous users should not be able to create an order."""
        product = factories.ProductFactory()
        data = {
            "course": product.courses.first().code,
            "product": str(product.uid),
        }
        response = self.client.post(
            "/api/orders/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_create_authenticated_success(self):
        """Any authenticated user should be able to create an order."""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "product": str(product.uid),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()
        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "pending",
                "owner": "panoramix",
                "price": str(product.price),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
            },
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_api_order_create_and_pay_authenticated_success(self):
        """Any authenticated user should be able to create and pay an order."""
        target_courses = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "name": "Personal",
                "card_number": "1111222233334444",
                "expiration_date": (
                    timezone.now() + datetime.timedelta(days=400)
                ).strftime("%m/%y"),
                "cryptogram": "222",
                "save": False,
            },
        }
        token = self.get_user_token("panoramix")

        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            # payment success log
            self.assertTrue("succeeded" in logs.output[0])
            self.assertEqual(response.status_code, 201)
            content = json.loads(response.content)

            # an order has been created with state paid
            self.assertEqual(models.Order.objects.count(), 1)
            order = models.Order.objects.get()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)
            self.assertEqual(
                content,
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "paid",
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_api_order_create_and_pay_and_register_credit_card_authenticated_success(
        self,
    ):
        """Any authenticated user should be able to create, pay an order and save credit card."""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "name": "Personal",
                "card_number": "1111222233334444",
                "expiration_date": (
                    timezone.now() + datetime.timedelta(days=400)
                ).strftime("%m/%y"),
                "cryptogram": "222",
                "save": True,
            },
        }
        token = self.get_user_token("panoramix")

        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 201)

            # payment success log
            self.assertTrue("succeeded" in logs.output[0])
            # registration credit card success log
            self.assertTrue("successfully registered" in logs.output[1])
            # a new credit has been created
            self.assertEqual(models.CreditCard.objects.count(), 1)
            # an order with state paid has been created
            self.assertEqual(models.Order.objects.count(), 1)
            order = models.Order.objects.get()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)

            # check content returned
            self.assertEqual(
                json.loads(response.content),
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "paid",  # order state
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            # now try to pay an order with credit card just registered
            target_courses = factories.CourseFactory.create_batch(2)
            product = factories.ProductFactory(target_courses=target_courses)
            course = product.courses.first()
            credit_card = order.owner.creditcards.get()

            data = {
                "course": course.code,
                "product": str(product.uid),
                "credit_card": {
                    "id": credit_card.uid,
                },
            }
            token = self.get_user_token("panoramix")
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 201)

            # oneclick payment success log
            self.assertTrue("Oneclick payment" in logs.output[0])
            self.assertTrue("succeeded" in logs.output[0])

            # a new order with state paid has been created
            self.assertEqual(models.Order.objects.count(), 2)
            order = models.Order.objects.last()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)
            self.assertEqual(
                json.loads(response.content),
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "paid",
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.failing.FailingBackend"
    )
    def test_api_order_create_and_pay_failing_service(self):
        """Any authenticated user should be able to create but not pay an order
        if case of payment service failure."""
        target_courses = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "name": "Personal",
                "card_number": "1111222233334444",
                "expiration_date": (
                    timezone.now() + datetime.timedelta(days=400)
                ).strftime("%m/%y"),
                "cryptogram": "222",
                "save": False,
            },
        }
        token = self.get_user_token("panoramix")

        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            # payment failure log
            self.assertTrue("failed" in logs.output[0])
            self.assertEqual(response.status_code, 201)
            content = json.loads(response.content)

            # an order has been created but with state payment failed
            self.assertEqual(models.Order.objects.count(), 1)
            order = models.Order.objects.get()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAYMENT_FAILED)
            self.assertEqual(
                content,
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "payment_failed",
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.failing.FailingBackend"
    )
    def test_api_order_create_and_pay_and_register_credit_card_failing_service(self):
        """Any authenticated user should be able to create an order
        despite payment service failure"""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        card_number = "1111222233334444"
        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "name": "Personal",
                "card_number": card_number,
                "expiration_date": (
                    timezone.now() + datetime.timedelta(days=400)
                ).strftime("%m/%y"),
                "cryptogram": "222",
                "save": True,
            },
        }
        token = self.get_user_token("panoramix")

        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 201)

            # payment failing log
            self.assertTrue("failed" in logs.output[0])
            # registration credit card failure log
            self.assertTrue(
                f"Registration credit card ****{card_number[-4:]} failed"
                in logs.output[1]
            )
            # no credit card has been created
            self.assertFalse(models.CreditCard.objects.exists())
            # an order with state payment failed has been created
            self.assertEqual(models.Order.objects.count(), 1)
            order = models.Order.objects.get()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAYMENT_FAILED)

            # check content returned
            self.assertEqual(
                json.loads(response.content),
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "payment_failed",  # order state
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_api_order_create_and_pay_with_bad_credit_card_data(self):
        """Any authenticated user should be able to create and pay an order
        but user has to give full credit card data to pay"""
        token = self.get_user_token("panoramix")

        target_courses = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        # send data with missing values for credit card
        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "name": "Personal",
                "expiration_date": (
                    timezone.now() + datetime.timedelta(days=400)
                ).strftime("%m/%y"),
                "save": False,
            },
        }

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        # an order has been created but with pending state
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()
        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "pending",
                "owner": "panoramix",
                "price": str(product.price),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
            },
        )

        # now with bad credit card uid
        target_courses = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        course = product.courses.first()

        data = {
            "course": course.code,
            "product": str(product.uid),
            "credit_card": {
                "id": "nawak",
            },
        }

        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            # payment failure log
            self.assertTrue("failed" in logs.output[0])
            self.assertEqual(response.status_code, 201)
            content = json.loads(response.content)

            # an other order has been created but with payment_failed state
            self.assertEqual(models.Order.objects.count(), 2)
            order = models.Order.objects.last()
            self.assertEqual(
                list(order.target_courses.order_by("product_relations")), target_courses
            )
            self.assertEqual(order.state, enums.ORDER_STATE_PAYMENT_FAILED)
            self.assertEqual(
                content,
                {
                    "id": str(order.uid),
                    "course": course.code,
                    "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "state": "payment_failed",
                    "owner": "panoramix",
                    "price": str(product.price),
                    "product": str(product.uid),
                    "enrollments": [],
                    "target_courses": [
                        c.code
                        for c in product.target_courses.order_by("product_relations")
                    ],
                },
            )

            # now try to paid with credit card of an other user
            target_courses = factories.CourseFactory.create_batch(3)
            product = factories.ProductFactory(target_courses=target_courses)
            course = product.courses.first()
            not_owned_credit_card = factories.CreditCardFactory()
            data = {
                "course": course.code,
                "product": str(product.uid),
                "credit_card": {
                    "id": not_owned_credit_card.uid,
                },
            }

            with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
                response = self.client.post(
                    "/api/orders/",
                    data=data,
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                # payment failure log
                self.assertTrue("not found" in logs.output[0])
                self.assertEqual(response.status_code, 201)
                content = json.loads(response.content)

                # an other order has been created but with state payment_failed
                self.assertEqual(models.Order.objects.count(), 3)
                order = models.Order.objects.last()
                self.assertEqual(
                    list(order.target_courses.order_by("product_relations")),
                    target_courses,
                )
                self.assertEqual(order.state, enums.ORDER_STATE_PAYMENT_FAILED)
                self.assertEqual(
                    content,
                    {
                        "id": str(order.uid),
                        "course": course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "state": "payment_failed",
                        "owner": "panoramix",
                        "price": str(product.price),
                        "product": str(product.uid),
                        "enrollments": [],
                        "target_courses": [
                            c.code
                            for c in product.target_courses.order_by(
                                "product_relations"
                            )
                        ],
                    },
                )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        product = factories.ProductFactory(title="balançoire")
        course = factories.CourseFactory(title="mathématiques")

        data = {
            "course": course.code,
            "product": str(product.uid),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            content,
            {
                "__all__": [
                    'The product "balançoire" is not linked to course "mathématiques".'
                ]
            },
        )

    def test_api_order_delete_anonymous(self):
        """Anonymous users should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.delete("/api/orders/{!s}/".format(order.id))

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an order
        whether or not he/she is staff or even superuser.
        """
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        response = self.client.delete(
            "/api/orders/{!s}/".format(order.id),
            HTTP_AUTHORIZATION="Bearer {!s}".format(token),
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_owner(self):
        """The order owner should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token(order.owner.username)

        response = self.client.delete(
            "/api/orders/{!s}/".format(order.id),
            HTTP_AUTHORIZATION="Bearer {!s}".format(token),
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    # pylint: disable=too-many-locals
    def _check_api_order_update_detail(self, order, user, error_code):
        """Nobody should be allowed to update an order."""
        owner_token = self.get_user_token(order.owner.username)

        response = self.client.get(
            "/api/orders/{!s}/".format(order.uid),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {owner_token}",
        )
        data = json.loads(response.content)

        # Get data for another product we will use as alternative values
        # to try to modify our order
        other_owner = factories.UserFactory(is_superuser=random.choice([True, False]))
        *other_target_courses, _other_course = factories.CourseFactory.create_batch(3)
        other_product = factories.ProductFactory(target_courses=other_target_courses)
        other_order = factories.OrderFactory(owner=other_owner, product=other_product)
        other_owner_token = self.get_user_token(other_owner.username)

        other_response = self.client.get(
            "/api/orders/{!s}/".format(other_order.uid),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other_owner_token}",
        )
        other_data = json.loads(other_response.content)
        other_data["id"] = uuid.uuid4()

        # Try modifying the order on each field with our alternative data
        self.assertEqual(
            list(data.keys()),
            [
                "id",
                "course",
                "created_on",
                "enrollments",
                "owner",
                "price",
                "product",
                "state",
                "target_courses",
            ],
        )
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.get_user_token(user.username)}"}
            if user
            else {}
        )
        for field in data:
            initial_value = data[field]

            # With full object
            data[field] = other_data[field]
            response = self.client.put(
                "/api/orders/{!s}/".format(order.uid),
                data=data,
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # With partial object
            response = self.client.patch(
                "/api/orders/{!s}/".format(order.uid),
                data={field: other_data[field]},
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # Check that nothing was modified
            self.assertEqual(models.Order.objects.count(), 2)
            response = self.client.get(
                "/api/orders/{!s}/".format(order.uid),
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {owner_token}",
            )
            new_data = json.loads(response.content)
            self.assertEqual(new_data[field], initial_value)

    def test_api_order_update_detail_anonymous(self):
        """An anonymous user should not be allowed to update any order."""
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, None, 401)

    def test_api_order_update_detail_authenticated_superuser(self):
        """An authenticated superuser should not be allowed to update any order."""
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, user, 405)

    def test_api_order_update_detail_authenticated_owner(self):
        """The owner of an order should not be allowed to update his/her order."""
        owner = factories.UserFactory(is_superuser=True, is_staff=True)
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(owner=owner, product=product)
        self._check_api_order_update_detail(order, owner, 405)
