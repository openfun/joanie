"""Test suite for utils order methods"""

from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories, models
from joanie.core.utils.order import (
    delete_stuck_certificate_order,
    delete_stuck_orders,
    delete_stuck_signing_order,
    get_prepaid_order,
    verify_voucher,
)


class UtilsOrderTestCase(TestCase):
    """Test suite for utils order methods"""

    def test_utils_delete_stuck_signing_order(self):
        """
        Calling the method `delete_stuck_signing_order` should only delete the order and the
        related objects if the state is `to_sign` or `signing`.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(state=state)
                delete_stuck_signing_order(order)
                if state in [enums.ORDER_STATE_TO_SIGN, enums.ORDER_STATE_SIGNING]:
                    self.assertFalse(models.Order.objects.filter(pk=order.pk).exists())
                else:
                    self.assertTrue(models.Order.objects.filter(pk=order.pk).exists())

    def test_utils_delete_stuck_certificate_order(self):
        """
        When we call the method `delete_stuck_certificate_order` it should only delete the orders
        with a product type certificate that are in the state `to_save_payment_method`.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                enrollment = factories.EnrollmentFactory()
                product = factories.ProductFactory(
                    courses=[enrollment.course_run.course],
                    price=100.00,
                    type=enums.PRODUCT_TYPE_CERTIFICATE,
                )
                order = factories.OrderFactory(
                    course=None,
                    enrollment=enrollment,
                    product=product,
                    state=state,
                )
                delete_stuck_certificate_order(order)
                if state == enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD:
                    self.assertFalse(models.Order.objects.filter(pk=order.pk).exists())
                else:
                    self.assertTrue(models.Order.objects.filter(pk=order.pk).exists())

    def test_utils_delete_stuck_certificate_order_should_not_delete_credential_orders(
        self,
    ):
        """
        No matter the state of the order, if the product type is credential, then the method
        `delete_stuck_certificate_order` should not delete any orders.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderFactory(
                    product__type=enums.PRODUCT_TYPE_CREDENTIAL,
                    state=state,
                )
                delete_stuck_certificate_order(order)
                self.assertTrue(models.Order.objects.filter(pk=order.pk).exists())

    def test_utils_delete_stuck_certificate_should_not_delete_enrollment_orders(self):
        """
        No matter the state of the order, if the product type is enrollment, then the method
        `delete_stuck_certificate_order` should not delete any orders.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                enrollment_product = factories.ProductFactory(
                    type=enums.PRODUCT_TYPE_ENROLLMENT
                )
                order = factories.OrderFactory(product=enrollment_product, state=state)
                delete_stuck_certificate_order(order)
                self.assertTrue(models.Order.objects.filter(pk=order.pk).exists())

    def test_utils_delete_stuck_orders(self):
        """
        The method `delete_stuck_order` should delete only orders that are in signing
        states and orders with product certificates in the state `to_save_payment_method`.
        """
        # Create orders that will be deleted
        factories.OrderGeneratorFactory.create_batch(2, state=enums.ORDER_STATE_TO_SIGN)
        factories.OrderGeneratorFactory.create_batch(2, state=enums.ORDER_STATE_SIGNING)
        enrollments = factories.EnrollmentFactory.create_batch(2)
        factories.OrderFactory(
            course=None,
            enrollment=enrollments[0],
            product__courses=[enrollments[0].course_run.course],
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        )
        stuck_order = factories.OrderFactory(
            course=None,
            enrollment=enrollments[1],
            product__courses=[enrollments[1].course_run.course],
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        )
        # Prepare time tolerance of latest update of order objects for those specific states
        beyond_tolerated_time = stuck_order.updated_on + timedelta(
            seconds=settings.JOANIE_ORDER_UPDATE_DELAY_LIMIT_IN_SECONDS
        )
        within_time_tolerated = beyond_tolerated_time - timedelta(seconds=60)
        # Create orders that will not be deleted
        kept_orders = [
            factories.OrderFactory(
                product__type=enums.PRODUCT_TYPE_CREDENTIAL,
                state=enums.ORDER_STATE_CANCELED,
                updated_on=within_time_tolerated,
            )
        ]
        kept_orders.extend(
            factories.OrderGeneratorFactory.create_batch(
                3, state=enums.ORDER_STATE_DRAFT, updated_on=within_time_tolerated
            )
        )
        kept_orders.extend(
            factories.OrderGeneratorFactory.create_batch(
                3,
                state=enums.ORDER_STATE_PENDING_PAYMENT,
                updated_on=within_time_tolerated,
            )
        )

        with mock.patch(
            "django.utils.timezone.now", return_value=beyond_tolerated_time
        ):
            (
                deleted_orders_in_signing_states,
                deleted_orders_in_to_save_payment_state,
            ) = delete_stuck_orders()

        self.assertEqual(deleted_orders_in_signing_states, 4)
        self.assertEqual(deleted_orders_in_to_save_payment_state, 2)
        # Check that the orders we created to control still exists
        self.assertListEqual(kept_orders, list(models.Order.objects.all().reverse()))

    def test_utils_verify_voucher(self):
        """
        The method `verify_voucher` will verify if the passed voucher code exists and is active
        into our database before letting a user use it. It returns the voucher if found, else
        it returns None.
        """
        active_voucher = factories.VoucherFactory(is_active=True)
        non_active_voucher = factories.VoucherFactory(is_active=False)

        self.assertTrue(verify_voucher(active_voucher.code))
        self.assertIsNone(verify_voucher(non_active_voucher.code))
        self.assertIsNone(verify_voucher("random_code"))

    def test_utils_get_prepaid_order(self):
        """
        The method `get_prepaid_order` should return the order in state `to_own` that was
        generated from a batch order. When the course and product and voucher code information
        are correct, it should return the Order object, else it returns None.
        """
        [offering_1, offering_2] = factories.OfferingFactory.create_batch(
            2,
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        batch_order = factories.BatchOrderFactory(
            offering=offering_1,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )
        batch_order.generate_orders()
        order = batch_order.orders.all()[0]

        self.assertIsNone(
            get_prepaid_order(
                offering_2.course.code, offering_2.product.id, order.voucher.code
            )
        )
        self.assertIsNone(
            get_prepaid_order(
                offering_1.course.code, offering_2.product.id, order.voucher.code
            )
        )
        self.assertIsNone(
            get_prepaid_order(
                offering_2.course.code, offering_1.product.id, order.voucher.code
            )
        )
        self.assertIsNone(
            get_prepaid_order(
                offering_1.course.code, offering_1.product.id, "random_code"
            )
        )
        self.assertTrue(
            get_prepaid_order(
                offering_1.course.code, offering_1.product.id, order.voucher.code
            )
        )
