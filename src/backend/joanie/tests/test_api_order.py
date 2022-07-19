"""Tests for the Order API."""
import json
import random
import uuid
from io import BytesIO
from unittest import mock

from django.core.cache import cache

from djmoney.money import Money
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.exceptions import CreatePaymentFailed
from joanie.payment.factories import (
    BillingAddressDictFactory,
    CreditCardFactory,
    ProformaInvoiceFactory,
)

from .base import BaseAPITestCase


class OrderApiTest(BaseAPITestCase):
    """Test the API of the Order object."""

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

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
                        "issued_certificate": None,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "id": str(order.uid),
                        "owner": order.owner.username,
                        "total": float(product.price.amount),
                        "total_currency": str(product.price.currency),
                        "product": str(order.product.uid),
                        "main_proforma_invoice": None,
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
                        "issued_certificate": None,
                        "course": other_order.course.code,
                        "created_on": other_order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_proforma_invoice": None,
                        "owner": other_order.owner.username,
                        "total": float(other_order.total.amount),
                        "total_currency": str(other_order.total.currency),
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

        response = self.client.get(f"/api/orders/{order.uid}/")
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
            f"/api/orders/{order.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "issued_certificate": None,
                "course": order.course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": order.state,
                "main_proforma_invoice": None,
                "owner": owner.username,
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
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
            f"/api/orders/{order.uid}/",
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
        product = factories.ProductFactory(
            target_courses=target_courses, price=Money("0.00", "EUR")
        )
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
                "issued_certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "validated",
                "main_proforma_invoice": None,
                "owner": "panoramix",
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
            },
        )

    def test_api_order_create_has_read_only_fields(self):
        """
        If an authenticated user tries to create an order with more fields than
        "product" and "course", it should not be allowed to override these fields.
        """
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            target_courses=target_courses, price=Money(0.00, "EUR")
        )
        course = product.courses.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "product": str(product.uid),
            "id": uuid.uuid4(),
            "amount": 0.00,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # - Order has been successfully created and read_only_fields
        #   has been ignored.
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()

        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )

        # - id, price and state has not been set according to data values
        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "issued_certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "validated",
                "main_proforma_invoice": None,
                "owner": "panoramix",
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
            },
        )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        product = factories.ProductFactory(
            title="balançoire", price=Money("0.00", "EUR")
        )
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

    def test_api_order_create_authenticated_missing_product_then_course(self):
        """The payload must contain at least a product uid and a course code."""
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            content,
            {
                "course": ["This field is required."],
                "product": ["This field is required."],
            },
        )

    def test_api_order_create_once(self):
        """
        If a user tries to create a new order while he has already a not canceled order
        for the couple product - course, a bad request response should be returned.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=Money("0.00", "EUR"))

        # User already owns an order for this product and course
        order = factories.OrderFactory(owner=user, course=course, product=product)

        data = {"product": str(product.uid), "course": course.code}

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content),
            (
                f"Cannot create order related to the product {product.uid} "
                f"and course {course.code}"
            ),
        )

        # But if we cancel the first order, user should be able to create a new order
        order.cancel()

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)

    def test_api_order_create_payment_requires_billing_address(self):
        """
        To create an order related to a fee product, a payment is created. In order
        to create it, user should provide a billing address. If this information is
        missing, api should return a Bad request.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[course])

        data = {"product": str(product.uid), "course": course.code}

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"billing_address": "This field is required."})

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    def test_api_order_create_payment(self, mock_create_payment):
        """
        Create an order to a fee product should create a payment at the same time and
        bind payment information into the response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        billing_address = BillingAddressDictFactory()

        data = {
            "product": str(product.uid),
            "course": course.code,
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        mock_create_payment.assert_called_once()

        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "issued_certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "pending",
                "main_proforma_invoice": None,
                "owner": user.username,
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
                "payment_info": {
                    "payment_id": f"pay_{order.uid}",
                    "provider": "dummy",
                    "url": "http://testserver/api/payments/notifications",
                },
            },
        )

    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    def test_api_order_create_payment_with_registered_credit_card(
        self, mock_create_one_click_payment
    ):
        """
        Create an order to a fee product should create a payment. If user provides
        a credit card id, a one click payment should be triggered and within response
        payment information should contain `is_paid` property.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        credit_card = CreditCardFactory(owner=user)
        billing_address = BillingAddressDictFactory()

        data = {
            "product": str(product.uid),
            "course": course.code,
            "billing_address": billing_address,
            "credit_card_id": str(credit_card.uid),
        }

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        mock_create_one_click_payment.assert_called_once()

        self.assertEqual(
            content,
            {
                "id": str(order.uid),
                "issued_certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "validated",
                "main_proforma_invoice": order.main_proforma_invoice.reference,
                "owner": user.username,
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.uid),
                "enrollments": [],
                "target_courses": [
                    c.code for c in product.target_courses.order_by("product_relations")
                ],
                "payment_info": {
                    "payment_id": f"pay_{order.uid}",
                    "provider": "dummy",
                    "url": "http://testserver/api/payments/notifications",
                    "is_paid": True,
                },
            },
        )

    @mock.patch.object(DummyPaymentBackend, "create_payment")
    def test_api_order_create_payment_failed(self, mock_create_payment):
        """
        If payment creation failed, any order should be created.
        """
        mock_create_payment.side_effect = CreatePaymentFailed("Unreachable endpoint")
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        billing_address = BillingAddressDictFactory()

        data = {
            "product": str(product.uid),
            "course": course.code,
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": "Unreachable endpoint"})

    def test_api_order_delete_anonymous(self):
        """Anonymous users should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.delete(f"/api/orders/{order.uid}/")

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
            f"/api/orders/{order.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_owner(self):
        """The order owner should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token(order.owner.username)

        response = self.client.delete(
            f"/api/orders/{order.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    # pylint: disable=too-many-locals
    def _check_api_order_update_detail(self, order, user, error_code):
        """Nobody should be allowed to update an order."""
        owner_token = self.get_user_token(order.owner.username)

        response = self.client.get(
            f"/api/orders/{order.uid}/",
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
            f"/api/orders/{other_order.uid}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other_owner_token}",
        )
        other_data = json.loads(other_response.content)
        other_data["id"] = uuid.uuid4()

        # Try modifying the order on each field with our alternative data
        self.assertEqual(
            list(data.keys()),
            [
                "course",
                "created_on",
                "issued_certificate",
                "enrollments",
                "id",
                "main_proforma_invoice",
                "owner",
                "total",
                "total_currency",
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
                f"/api/orders/{order.uid}/",
                data=data,
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # With partial object
            response = self.client.patch(
                f"/api/orders/{order.uid}/",
                data={field: other_data[field]},
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # Check that nothing was modified
            self.assertEqual(models.Order.objects.count(), 2)
            response = self.client.get(
                f"/api/orders/{order.uid}/",
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

    def test_api_order_get_proforma_invoice_anonymous(self):
        """An anonymous user should not be allowed to retrieve a pro forma invoice."""
        proforma_invoice = ProformaInvoiceFactory()

        response = self.client.get(
            (
                f"/api/orders/{proforma_invoice.order.uid}/proforma_invoice/"
                f"?reference={proforma_invoice.reference}"
            ),
        )

        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)

        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_get_proforma_invoice_authenticated_user_with_no_reference(self):
        """
        If an authenticated user tries to retrieve order's pro forma invoice
        without reference parameter, it should return a bad request response.
        """
        proforma_invoice = ProformaInvoiceFactory()
        token = self.get_user_token(proforma_invoice.order.owner.username)

        response = self.client.get(
            f"/api/orders/{proforma_invoice.order.uid}/proforma_invoice/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"reference": "This parameter is required."})

    def test_api_order_get_proforma_invoice_not_linked_to_order(self):
        """
        An authenticated user should not be allowed to retrieve a pro forma invoice
        not linked to the current order
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()
        proforma_invoice = ProformaInvoiceFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/orders/{order.uid}/proforma_invoice/?reference={proforma_invoice.reference}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(
            content,
            (
                f"No pro forma invoice found for order {order.uid} "
                f"with reference {proforma_invoice.reference}."
            ),
        )

    def test_api_order_get_proforma_invoice_authenticated_user_not_owner(self):
        """
        An authenticated user should not be allowed to retrieve
        a pro forma invoice not owned by himself
        """
        user = factories.UserFactory()
        proforma_invoice = ProformaInvoiceFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            (
                f"/api/orders/{proforma_invoice.order.uid}/proforma_invoice/"
                f"?reference={proforma_invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(
            content,
            (
                f"No pro forma invoice found for order {proforma_invoice.order.uid} "
                f"with reference {proforma_invoice.reference}."
            ),
        )

    def test_api_order_get_proforma_invoice_authenticated_owner(self):
        """
        An authenticated user which owns the related order should be able to retrieve
        a related pro forma invoice through its reference
        """
        proforma_invoice = ProformaInvoiceFactory()
        token = self.get_user_token(proforma_invoice.order.owner.username)

        response = self.client.get(
            (
                f"/api/orders/{proforma_invoice.order.uid}/proforma_invoice/"
                f"?reference={proforma_invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={proforma_invoice.reference}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"INVOICE")

    def test_api_order_abort_anonymous(self):
        """An anonymous user should not be allowed to abort an order"""
        order = factories.OrderFactory()

        response = self.client.post(f"/api/orders/{order.uid}/abort/")

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_abort_authenticated_user_not_owner(self):
        """
        An authenticated user which is not the owner of the order should not be
        allowed to abort the order.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()

        token = self.get_user_token(user.username)
        response = self.client.post(
            f"/api/orders/{order.uid}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            content, f'No order found with id "{order.uid}" owned by {user.username}.'
        )

    def test_api_order_abort_not_pending(self):
        """
        An authenticated user which is the owner of the order should not be able
        to abort the order if it is not pending.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory(price=Money("0.00", "EUR"))
        order = factories.OrderFactory(owner=user, product=product)

        token = self.get_user_token(user.username)
        response = self.client.post(
            f"/api/orders/{order.uid}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(content, "Cannot abort a not pending order.")

    @mock.patch.object(
        DummyPaymentBackend,
        "abort_payment",
        side_effect=DummyPaymentBackend().abort_payment,
    )
    def test_api_order_abort(self, mock_abort_payment):
        """
        An authenticated user which is the owner of the order should be able to abort
        the order if it is pending and abort the related payment if a payment_id is
        provided.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        billing_address = BillingAddressDictFactory()

        # - Create an order and its related payment
        token = self.get_user_token(user.username)
        data = {
            "product": str(product.uid),
            "course": course.code,
            "billing_address": billing_address,
        }
        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = json.loads(response.content)
        order = models.Order.objects.get(uid=content["id"])
        payment_id = content["payment_info"]["payment_id"]

        # - A pending order should have been created...
        self.assertEqual(response.status_code, 201)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # - ... with a payment
        self.assertIsNotNone(cache.get(payment_id))

        # - User asks to abort the order
        response = self.client.post(
            f"/api/orders/{order.uid}/abort/",
            data={"payment_id": payment_id},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 204)

        # - Order should have been canceled ...
        order.refresh_from_db()
        self.assertEqual(order.is_canceled, True)

        # - and its related payment should have been aborted.
        mock_abort_payment.assert_called_once_with(payment_id)
        self.assertIsNone(cache.get(payment_id))
