"""Test suite for the Skill model."""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import override

from joanie.core.factories import SkillFactory


class SkillModelTestCase(TestCase):
    """Test suite for the Skill model."""

    def test_models_skill_title_uniqueness(self):
        """Test that the title of a skill is unique."""
        SkillFactory(title="Uniqueness")

        # Uniqueness is case-insensitive
        with self.assertRaises(ValidationError) as error:
            SkillFactory(title="uniqueness")

        self.assertEqual(
            error.exception.messages[0], "A skill with this title already exists."
        )

        # Uniqueness is language sensitive
        with override("fr"):
            SkillFactory(title="Uniqueness")

    def test_models_skill_sanitize_title(self):
        """
        Test that the title of a skill is sanitized
        (Extra whitespaces should be removed).
        """
        skill = SkillFactory(title="  Hello     World    ")

        self.assertEqual(skill.title, "Hello World")
