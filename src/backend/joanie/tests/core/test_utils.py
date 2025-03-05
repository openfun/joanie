"""Test core utils."""

from django.test import TestCase

from joanie.core.utils import generate_random_code, merge_dict


class UtilsTestCase(TestCase):
    """Validate that utils in the core app work as expected."""

    def test_utils_merge_dict(self):
        """Update a deep nested dictionary with another deep nested dictionary."""
        dict_1 = {"k1": {"k11": {"a": 0, "b": 1}}}
        dict_2 = {"k1": {"k11": {"b": 10}, "k12": {"a": 3}}}
        self.assertEqual(
            merge_dict(dict_1, dict_2),
            {"k1": {"k11": {"a": 0, "b": 10}, "k12": {"a": 3}}},
        )

    def test_utils_generate_random_code(self):
        """Generate a random code."""
        code = generate_random_code()

        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 18)
        self.assertTrue(code.isalnum())
        self.assertTrue(code.isascii())
