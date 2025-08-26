"""
Test suite for the "synchronize_course_runs" utility
"""

import json
import random
import re
from http import HTTPStatus
from logging import Logger
from unittest import mock

from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.core.utils import webhooks


class SynchronizeCourseRunsUtilsTestCase(TestCase):
    """Test suite for the `synchronize_course_runs` utility."""

    def _get_serialized_course_run(self, index):
        """Return a"""
        return {
            "resource_link": f"https://example.com/products/{index:d}",
            "start": f"2022-12-0{index:d}T09:00:00+00:00",
            "end": f"2022-12-0{index:d}T19:00:00+00:00",
            "enrollment_start": f"2022-11-0{index:d}T08:00:00+00:00",
            "enrollment_end": f"2022-12-0{index:d}T10:00:00+00:00",
            "catalog_visibility": "course_and_search",
            "course": str(index),
        }

    def test_utils_synchronize_course_runs_no_hooks(self):
        """If no webhook is declared the function should not make any request."""
        with override_settings(COURSE_WEB_HOOKS=[]), responses.RequestsMock():
            webhooks.synchronize_course_runs([self._get_serialized_course_run(1)])

        self.assertEqual(len(responses.calls), 0)

    def test_utils_synchronize_course_runs_no_course_runs(self):
        """If no course runs are passed as arguments, the method should not make any request."""
        with (
            override_settings(
                COURSE_WEB_HOOKS=[
                    {"url": "http://richie.education/webhook", "secret": "abc"},
                ]
            ),
            responses.RequestsMock(),
        ):
            webhooks.synchronize_course_runs([])

        self.assertEqual(len(responses.calls), 0)

    @mock.patch.object(Logger, "info")
    def test_utils_synchronize_course_runs_success(self, mock_info):
        """Course runs passed to the function should get synchronized."""
        with (
            override_settings(
                COURSE_WEB_HOOKS=[
                    {"url": "http://richie.education/webhook1", "secret": "abc"},
                    {"url": "http://richie.education/webhook2", "secret": "abc"},
                ]
            ),
            responses.RequestsMock() as rsps,
        ):
            # Ensure successful response by webhook using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook{1}"),
                body="{}",
                status=HTTPStatus.OK,
                content_type="application/json",
            )

            webhooks.synchronize_course_runs(
                [self._get_serialized_course_run(1), self._get_serialized_course_run(2)]
            )

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
                    "resource_link": "https://example.com/products/1",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-01T19:00:00+00:00",
                    "enrollment_start": "2022-11-01T08:00:00+00:00",
                    "enrollment_end": "2022-12-01T10:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "1",
                },
                {
                    "resource_link": "https://example.com/products/2",
                    "start": "2022-12-02T09:00:00+00:00",
                    "end": "2022-12-02T19:00:00+00:00",
                    "enrollment_start": "2022-11-02T08:00:00+00:00",
                    "enrollment_end": "2022-12-02T10:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "2",
                },
            ]
            payload1 = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload1, expected_payload)
            payload2 = json.loads(rsps.calls[1].request.body)
            self.assertCountEqual(payload2, expected_payload)

            # Signature
            expected_signature = (
                "SIG-HMAC-SHA256 "
                "0d7f818abb1fb74a5abaf51b29ee3c15976873c0ce96439248902ea66a942d48"
            )
            self.assertEqual(
                rsps.calls[0].request.headers["Authorization"], expected_signature
            )
            self.assertEqual(
                rsps.calls[1].request.headers["Authorization"], expected_signature
            )

            # Logger
            self.assertEqual(mock_info.call_count, 4)
            self.assertEqual(
                mock_info.call_args_list[2][0],
                (
                    "[SYNC] Synchronization succeeded with %s",
                    "http://richie.education/webhook1",
                ),
            )
            self.assertEqual(
                mock_info.call_args_list[3][0],
                (
                    "[SYNC] Synchronization succeeded with %s",
                    "http://richie.education/webhook2",
                ),
            )

    @mock.patch.object(Logger, "error")
    def test_utils_synchronize_course_runs_failure(self, mock_error):
        """The logger should be called on webhook call failure."""
        with (
            override_settings(
                COURSE_WEB_HOOKS=[
                    {"url": "http://richie.education/webhook", "secret": "abc"},
                ]
            ),
            responses.RequestsMock() as rsps,
        ):
            # Simulate webhook failure using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook"),
                body="{}",
                status=random.choice(
                    [
                        HTTPStatus.NOT_FOUND,
                        HTTPStatus.BAD_GATEWAY,
                        HTTPStatus.MOVED_PERMANENTLY,
                    ]
                ),
                content_type="application/json",
            )

            webhooks.synchronize_course_runs([self._get_serialized_course_run(1)])

            self.assertEqual(rsp.call_count, 1)
            # Webhook urls called
            self.assertEqual(
                rsps.calls[0].request.url, "http://richie.education/webhook"
            )

            # Payload sent to webhooks
            expected_payload = [
                {
                    "resource_link": "https://example.com/products/1",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-01T19:00:00+00:00",
                    "enrollment_start": "2022-11-01T08:00:00+00:00",
                    "enrollment_end": "2022-12-01T10:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "1",
                },
            ]
            payload = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload, expected_payload)

            # Signature
            expected_signature = (
                "SIG-HMAC-SHA256 "
                "22c2e3fac8557ed4035d47c2b7ab4e2a2671eafc2725251dd55269747474d091"
            )
            self.assertEqual(
                rsps.calls[0].request.headers["Authorization"], expected_signature
            )

            # Logger
            self.assertEqual(mock_error.call_count, 1)
            self.assertEqual(
                mock_error.call_args_list[0][0],
                (
                    "[SYNC] Synchronization failed with %s",
                    "http://richie.education/webhook",
                ),
            )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(Logger, "info")
    def test_utils_synchronize_course_runs_retries(self, mock_info, mock_error):
        """Course runs synchronization supports retries."""
        expected_payload = [
            {
                "resource_link": "https://example.com/products/1",
                "start": "2022-12-01T09:00:00+00:00",
                "end": "2022-12-01T19:00:00+00:00",
                "enrollment_start": "2022-11-01T08:00:00+00:00",
                "enrollment_end": "2022-12-01T10:00:00+00:00",
                "catalog_visibility": "course_and_search",
                "course": "1",
            },
        ]
        with (
            override_settings(
                COURSE_WEB_HOOKS=[
                    {"url": "http://richie.education/webhook", "secret": "abc"},
                ]
            ),
            responses.RequestsMock(
                registry=responses.registries.OrderedRegistry
            ) as rsps,
        ):
            # Make webhook fail 3 times before succeeding using "responses"
            url = "http://richie.education/webhook"
            all_rsps = [
                rsps.post(url, status=HTTPStatus.INTERNAL_SERVER_ERROR),
                rsps.post(url, status=HTTPStatus.INTERNAL_SERVER_ERROR),
                rsps.post(url, status=HTTPStatus.INTERNAL_SERVER_ERROR),
                rsps.post(url, status=HTTPStatus.OK),
            ]

            webhooks.synchronize_course_runs([self._get_serialized_course_run(1)])

            for i in range(4):
                self.assertEqual(all_rsps[i].call_count, 1)
                self.assertEqual(
                    rsps.calls[i].request.url, "http://richie.education/webhook"
                )
                payload = json.loads(rsps.calls[i].request.body)
                self.assertCountEqual(payload, expected_payload)

            # Logger
            self.assertFalse(mock_error.called)
            self.assertEqual(mock_info.call_count, 3)
            self.assertEqual(
                mock_info.call_args_list[2][0],
                (
                    "[SYNC] Synchronization succeeded with %s",
                    "http://richie.education/webhook",
                ),
            )

    @mock.patch.object(Logger, "error")
    def test_utils_synchronize_course_runs_max_retries_exceeded(self, mock_error):
        """Course runs synchronization supports retries has exceeded max retries."""
        with (
            override_settings(
                COURSE_WEB_HOOKS=[
                    {"url": "http://richie.education/webhook", "secret": "abc"},
                ]
            ),
            responses.RequestsMock() as rsps,
        ):
            # Simulate webhook failure using "responses":
            rsp = rsps.post(
                re.compile("http://richie.education/webhook"),
                body="{}",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                content_type="application/json",
            )

            webhooks.synchronize_course_runs([self._get_serialized_course_run(1)])

            self.assertEqual(rsp.call_count, 5)
            # Webhook urls called
            self.assertEqual(
                rsps.calls[0].request.url, "http://richie.education/webhook"
            )

            # Payload sent to webhooks
            expected_payload = [
                {
                    "resource_link": "https://example.com/products/1",
                    "start": "2022-12-01T09:00:00+00:00",
                    "end": "2022-12-01T19:00:00+00:00",
                    "enrollment_start": "2022-11-01T08:00:00+00:00",
                    "enrollment_end": "2022-12-01T10:00:00+00:00",
                    "catalog_visibility": "course_and_search",
                    "course": "1",
                },
            ]
            payload = json.loads(rsps.calls[0].request.body)
            self.assertCountEqual(payload, expected_payload)

            # Signature
            expected_signature = (
                "SIG-HMAC-SHA256 "
                "22c2e3fac8557ed4035d47c2b7ab4e2a2671eafc2725251dd55269747474d091"
            )
            self.assertEqual(
                rsps.calls[0].request.headers["Authorization"], expected_signature
            )

            # Logger
            self.assertEqual(mock_error.call_count, 1)
            self.assertEqual(
                mock_error.call_args_list[0][0],
                (
                    "[SYNC] Synchronization failed due to max retries exceeded with url %s",
                    "http://richie.education/webhook",
                ),
            )
