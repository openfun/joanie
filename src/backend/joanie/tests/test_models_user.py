"""Test suite for badge models."""
from django.db import IntegrityError
from django.test import RequestFactory, TestCase

from joanie.core.factories import UserFactory
from joanie.core.models import User


class UserModelTestCase(TestCase):
    """Test suite for the User model."""

    def test_model_create(self):
        """A simple test to check model consistency."""

        UserFactory(username="Sam", email="sam@fun-test.fr", language="fr")
        UserFactory(username="Joanie")

        self.assertEqual(User.objects.count(), 2)

        first_user = User.objects.first()
        self.assertEqual(first_user.username, "Sam")
        self.assertEqual(first_user.email, "sam@fun-test.fr")
        self.assertEqual(first_user.language, "fr")
        self.assertEqual(str(first_user), "Sam")

    def test_models_unique_username(self):
        """
        There should be a db constraint forcing uniqueness of username
        """
        UserFactory(username="Sam", email="sam@fun-test.fr")

        with self.assertRaises(IntegrityError):
            UserFactory(username="Sam")

    def test_models_multiple_emails(self):
        """
        Multiple users can have the same email
        """
        UserFactory(username="Sam", email="mail@fun-test.fr")
        UserFactory(username="Joanie", email="mail@fun-test.fr")
        self.assertEqual(User.objects.filter(email="mail@fun-test.fr").count(), 2)

    def test_models_create_or_update_from_request(self):
        """
        Check using the method create_or_update_from_request, a user
        is created if non existing or else updated
        """
        user = UserFactory(username="Sam", email="mail@fun-test.fr")

        request = RequestFactory()
        request.username = "Sam"
        request.email = "sam@fun-test.fr"
        request.language = "fr"

        User.update_or_create_from_request_user(request)
        user.refresh_from_db()

        # email has been updated
        self.assertEqual(user.email, "sam@fun-test.fr")
        self.assertEqual(user.language, "fr")
        # no new object has been created
        self.assertEqual(User.objects.count(), 1)

        request.username = "Sam2"
        request.language = "en"
        User.update_or_create_from_request_user(request)
        # a new object has been created
        self.assertEqual(User.objects.count(), 2)
        user2 = User.objects.get(username="Sam2")
        self.assertEqual(user2.language, "en")
        self.assertEqual(user2.email, "sam@fun-test.fr")
