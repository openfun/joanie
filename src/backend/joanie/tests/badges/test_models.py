"""Test suite for badge models."""
from django.test import TestCase

from joanie.badges import factories, models
from joanie.core.factories import UserFactory


class BadgeModelTestCase(TestCase):
    """Test suite for the Badge model."""

    def test_model_create(self):
        """A simple test to check model consistency."""

        factories.BadgeFactory(name="foo")
        factories.BadgeFactory(name="bar")

        assert models.Badge.objects.count() == 2
        assert models.Badge.objects.first().name == "foo"

        badge = factories.BadgeFactory(provider="OBF", name="lol")
        assert str(badge) == "OBF: lol"


class IssuedBadgeModelTestCase(TestCase):
    """Test suite for the IssuedBadge model."""

    def test_model_create(self):
        """A simple test to check model consistency."""

        user = UserFactory()

        factories.IssuedBadgeFactory(user=user)
        factories.IssuedBadgeFactory(user=user)

        assert models.IssuedBadge.objects.count() == 2
        assert user.issued_badges.count() == 2
        assert models.Badge.objects.first().issued.count() == 1

        user = UserFactory(first_name="John", last_name="Doe")
        badge = factories.BadgeFactory(provider="OBF", name="foo")
        issued_badge = factories.IssuedBadgeFactory(user=user, badge=badge)
        assert str(issued_badge) == "OBF: foo - John Doe"
