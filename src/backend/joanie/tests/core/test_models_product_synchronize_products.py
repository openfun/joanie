"""
Test suite for the "synchronize_products" method
"""
import json
import random
import re
from logging import Logger
from unittest import mock

from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.core import factories, models


class SynchronizeProductsModelsTestCase(TestCase):
    """Test suite for the `synchronize_products` method."""

    def test_models_synchronize_products_no_hooks(self):
        """If no webhook is declared the method should not make any request."""
        product = factories.ProductFactory()

        with override_settings(COURSE_WEB_HOOKS=[]), responses.RequestsMock():
            models.Product.synchronize_products([product])

    def test_models_synchronize_products_no_products(self):
        """If no products are passed as arguments, the method should not make any request."""
        with override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook", "secret": "abc"},
            ]
        ), responses.RequestsMock():
            models.Product.synchronize_products([])

    def test_models_synchronize_products_no_courses(self):
        """
        If the products passed are not linked to any courses, the method should not make any
        request.
        """
        product = factories.ProductFactory(courses=[])

        with override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook", "secret": "abc"},
            ]
        ), responses.RequestsMock():
            models.Product.synchronize_products([product])

    @mock.patch.object(Logger, "info")
    def test_models_synchronize_products_success(self, mock_info):
        """Products attached to courses should get synchronized."""
        courses = [factories.CourseFactory(code=i) for i in range(4)]
        pid1 = "2a76d5ee-8310-4a28-8e7f-c34dbdc4dd8a"
        product1 = factories.ProductFactory(id=pid1, courses=courses[:2])
        pid2 = "b9643d11-206c-42e6-a4b7-e91d96c87ba2"
        product2 = factories.ProductFactory(id=pid2, courses=courses[2:])

        def get_course_run_data(product):
            return {
                "resource_link": f"https://example.com/products/{product.id}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
            }

        with mock.patch.object(
            models.Product,
            "get_equivalent_course_run_data",
            side_effect=get_course_run_data,
            autospec=True,  # bind instance to method call
        ), override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook1", "secret": "abc"},
                {"url": "http://richie.education/webhook2", "secret": "abc"},
            ]
        ), responses.RequestsMock() as rsps:
            # Ensure successful response by webhook using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook{1}"),
                body="{}",
                status=200,
                content_type="application/json",
            )

            models.Product.synchronize_products([product1, product2])

            self.assertEqual(rsp.call_count, 2)
            # Webhook urls called
            self.assertEqual(
                rsps.calls[0].request.url, "http://richie.education/webhook1"
            )
            self.assertEqual(
                rsps.calls[1].request.url, "http://richie.education/webhook2"
            )

            # Payload sent to webhooks
            expected_payload = [
                {
                    "resource_link": f"https://example.com/products/{pid1:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "0",
                },
                {
                    "resource_link": f"https://example.com/products/{pid1:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "1",
                },
                {
                    "resource_link": f"https://example.com/products/{pid2:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "2",
                },
                {
                    "resource_link": f"https://example.com/products/{pid2:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "3",
                },
            ]
            payload1 = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload1, expected_payload)
            payload2 = json.loads(rsps.calls[1].request.body)
            self.assertCountEqual(payload2, expected_payload)

            # Signature
            expected_signature = (
                "SIG-HMAC-SHA256 "
                "1138f4cc2dda6df98b3af5c978b296296d9879ac12c618d9c1c1e882fe716b64"
            )
            self.assertCountEqual(
                rsps.calls[0].request.headers["Authorization"], expected_signature
            )
            self.assertCountEqual(
                rsps.calls[1].request.headers["Authorization"], expected_signature
            )

            # Logger
            self.assertEqual(mock_info.call_count, 2)
            self.assertEqual(
                mock_info.call_args_list[0][0],
                (
                    "Synchronisation succeeded with %s",
                    "http://richie.education/webhook1",
                ),
            )
            self.assertEqual(
                mock_info.call_args_list[1][0],
                (
                    "Synchronisation succeeded with %s",
                    "http://richie.education/webhook2",
                ),
            )

    @mock.patch.object(Logger, "error")
    def test_models_synchronize_products_failure(self, mock_info):
        """The logger should be called on webhook call failure."""
        courses = [factories.CourseFactory(code=i) for i in range(2)]
        pid = "2a76d5ee-8310-4a28-8e7f-c34dbdc4dd8a"
        product = factories.ProductFactory(id=pid, courses=courses)

        def get_course_run_data(product):
            return {
                "resource_link": f"https://example.com/products/{product.id}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
            }

        with mock.patch.object(
            models.Product,
            "get_equivalent_course_run_data",
            side_effect=get_course_run_data,
            autospec=True,  # bind instance to method call
        ), override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook", "secret": "abc"},
            ]
        ), responses.RequestsMock() as rsps:
            # Simulate webhook failure using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook"),
                body="{}",
                status=random.choice(["404", "500", "301"]),
                content_type="application/json",
            )

            models.Product.synchronize_products([product])

            self.assertEqual(rsp.call_count, 1)
            # Webhook urls called
            self.assertEqual(
                rsps.calls[0].request.url, "http://richie.education/webhook"
            )

            # Payload sent to webhooks
            expected_payload = [
                {
                    "resource_link": f"https://example.com/products/{pid:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "0",
                },
                {
                    "resource_link": f"https://example.com/products/{pid:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "1",
                },
            ]
            payload = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload, expected_payload)

            # Signature
            expected_signature = (
                "SIG-HMAC-SHA256 "
                "4191365d84b6076e3e1e9e745480e5be244cc501ae7bc4afd98063a8b3d71e8d"
            )
            self.assertCountEqual(
                rsps.calls[0].request.headers["Authorization"], expected_signature
            )

            # Logger
            self.assertEqual(mock_info.call_count, 1)
            self.assertEqual(
                mock_info.call_args_list[0][0],
                (
                    "Synchronisation failed with %s",
                    "http://richie.education/webhook",
                ),
            )

    @mock.patch.object(Logger, "info")
    def test_models_synchronize_products_force_visibility(self, mock_info):
        """
        Products can be synchronized with visibility forced.
        """
        courses = [factories.CourseFactory(code=i) for i in range(2)]
        pid = "2a76d5ee-8310-4a28-8e7f-c34dbdc4dd8a"
        product = factories.ProductFactory(id=pid, courses=courses)

        def get_course_run_data(product):
            return {
                "resource_link": f"https://example.com/products/{product.id}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
            }

        with mock.patch.object(
            models.Product,
            "get_equivalent_course_run_data",
            side_effect=get_course_run_data,
            autospec=True,  # bind instance to method call
        ), override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook", "secret": "abc"},
            ]
        ), responses.RequestsMock() as rsps:
            # Ensure successful response by webhook using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook"),
                body="{}",
                status=200,
                content_type="application/json",
            )

            models.Product.synchronize_products([product], visibility="hidden")

            self.assertEqual(rsp.call_count, 1)
            # Webhook urls called
            self.assertEqual(
                rsps.calls[0].request.url, "http://richie.education/webhook"
            )

            # Payload sent to webhooks
            expected_payload = [
                {
                    "resource_link": f"https://example.com/products/{pid:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "hidden",
                    "course": "0",
                },
                {
                    "resource_link": f"https://example.com/products/{pid:s}",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-15T19:00:00+00:00",
                    "enrollment_start": "2022-11-20T09:00:00+00:00",
                    "enrollment_end": "2022-12-05T19:00:00+00:00",
                    "catalog_visibility": "hidden",
                    "course": "1",
                },
            ]
            payload = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload, expected_payload)

            # Logger
            self.assertEqual(mock_info.call_count, 1)
            self.assertEqual(
                mock_info.call_args_list[0][0],
                (
                    "Synchronisation succeeded with %s",
                    "http://richie.education/webhook",
                ),
            )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(Logger, "info")
    def test_models_synchronize_products_retries(self, mock_info, mock_error):
        """Product synchronization supports retries."""
        courses = [factories.CourseFactory(code=i) for i in range(2)]
        pid = "2a76d5ee-8310-4a28-8e7f-c34dbdc4dd8a"
        product = factories.ProductFactory(id=pid, courses=courses)

        expected_payload = [
            {
                "resource_link": f"https://example.com/products/{pid:s}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
                "course": "0",
            },
            {
                "resource_link": f"https://example.com/products/{pid:s}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
                "course": "1",
            },
        ]

        def get_course_run_data(product):
            return {
                "resource_link": f"https://example.com/products/{product.id}",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-15T19:00:00+00:00",
                "enrollment_start": "2022-11-20T09:00:00+00:00",
                "enrollment_end": "2022-12-05T19:00:00+00:00",
                "catalog_visibility": "course_and_search",
            }

        with mock.patch.object(
            models.Product,
            "get_equivalent_course_run_data",
            side_effect=get_course_run_data,
            autospec=True,  # bind instance to method call
        ), override_settings(
            COURSE_WEB_HOOKS=[
                {"url": "http://richie.education/webhook", "secret": "abc"},
            ]
        ), responses.RequestsMock(
            registry=responses.registries.OrderedRegistry
        ) as rsps:
            # Make webhook fail 3 times before succeeding using "responses"
            url = "http://richie.education/webhook"
            all_rsps = [
                rsps.post(url, status=500),
                rsps.post(url, status=500),
                rsps.post(url, status=500),
                rsps.post(url, status=200),
            ]

            models.Product.synchronize_products([product])

            for i in range(4):
                self.assertEqual(all_rsps[i].call_count, 1)
                self.assertEqual(
                    rsps.calls[i].request.url, "http://richie.education/webhook"
                )
                payload = json.loads(rsps.calls[i].request.body)
                self.assertCountEqual(payload, expected_payload)

            # Logger
            self.assertFalse(mock_error.called)
            self.assertEqual(mock_info.call_count, 1)
            self.assertEqual(
                mock_info.call_args_list[0][0],
                (
                    "Synchronisation succeeded with %s",
                    "http://richie.education/webhook",
                ),
            )
