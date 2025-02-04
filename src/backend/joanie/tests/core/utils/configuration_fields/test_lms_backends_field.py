"""Test suite for the LMSBackendsValue custom field."""

import json

from django.test import TestCase

from joanie.core.utils import LMSBackendsValue, LMSBackendValidator


class TestCaseLMSBackendsValue(TestCase):
    """Test suite for the LMSBackendsValue custom field."""

    def setUp(self):
        self.lms_configuration = {
            "API_TOKEN": "FakeEdXAPIKey",
            "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
            "BASE_URL": "http://edx:8073",
            "SELECTOR_REGEX": "^.*/courses/(?P<course_id>.*)/course/?$",
            "COURSE_REGEX": "^.*/courses/(?P<course_id>.*)/course/?$",
            "COURSE_RUN_SYNC_NO_UPDATE_FIELDS": ["languages"],
        }

    def test_lms_backends_value_return_list_of_configuration(self):
        """If all validation pass, the return value should be a list of configuration."""

        envvar = json.dumps([self.lms_configuration])
        value = LMSBackendsValue().to_python(envvar)

        self.assertIsInstance(value, list)
        self.assertEqual(len(value), 1)
        backend = value[0]
        self.assertIsInstance(backend, dict)
        self.assertEqual(backend["API_TOKEN"], "FakeEdXAPIKey")
        self.assertEqual(
            backend["BACKEND"], "joanie.lms_handler.backends.dummy.DummyLMSBackend"
        )
        self.assertEqual(backend["BASE_URL"], "http://edx:8073")
        self.assertEqual(
            backend["SELECTOR_REGEX"], "^.*/courses/(?P<course_id>.*)/course/?$"
        )
        self.assertEqual(
            backend["COURSE_REGEX"], "^.*/courses/(?P<course_id>.*)/course/?$"
        )
        self.assertEqual(backend["COURSE_RUN_SYNC_NO_UPDATE_FIELDS"], ["languages"])

    def test_lms_backends_value_validate_required_keys(self):
        """It should ensure that all required keys are defined."""

        for key in LMSBackendValidator.BACKEND_REQUIRED_KEYS:
            with self.subTest("Missing key", key=key):
                values = self.lms_configuration.copy()
                values.pop(key)
                envvar = json.dumps([values])

                with self.assertRaises(ValueError):
                    LMSBackendsValue().to_python(envvar)

    def test_lms_backends_value_validate_regex_properties(self):
        """It should ensure that the regex properties are valid."""

        invalid_regex = r"ˆ][$"

        # Both selector and course regex should be validated
        for key in ["SELECTOR_REGEX", "COURSE_REGEX"]:
            with self.subTest("Invalid regex", key=key):
                values = self.lms_configuration.copy()
                values[key] = invalid_regex
                envvar = json.dumps([values])

                with self.assertRaises(ValueError) as exception:
                    LMSBackendsValue().to_python(envvar)

                self.assertEqual(
                    str(exception.exception), "Invalid regex ˆ][$ in LMS Backend."
                )

    def test_lms_backends_value_validate_backend_path(self):
        """It should ensure that the backend path string is valid."""
        values = self.lms_configuration.copy()
        values["BACKEND"] = "invalid.path..to.backend"
        envvar = json.dumps([values])

        with self.assertRaises(ValueError) as exception:
            LMSBackendsValue().to_python(envvar)

        self.assertEqual(
            str(exception.exception),
            "invalid.path..to.backend must be a valid python module path string.",
        )

    def test_lms_backends_value_validate_no_update_fields_value(self):
        """
        It should ensure that the COURSE_RUN_SYNC_NO_UPDATE_FIELDS value is a list
        if defined
        """
        values = self.lms_configuration.copy()
        values.pop("COURSE_RUN_SYNC_NO_UPDATE_FIELDS")
        envvar = json.dumps([values])

        # No error should be raised if the value is not defined
        LMSBackendsValue().to_python(envvar)

        values.update({"COURSE_RUN_SYNC_NO_UPDATE_FIELDS": "invalid"})
        envvar = json.dumps([values])

        with self.assertRaises(ValueError) as exception:
            LMSBackendsValue().to_python(envvar)

        self.assertEqual(
            str(exception.exception), "COURSE_RUN_SYNC_NO_UPDATE_FIELDS must be a list."
        )
