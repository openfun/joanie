"""Test suite for badge models."""
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from joanie.core.factories import UserFactory
from joanie.core.models import User


class UserModelTestCase(TestCase):
    """Test suite for the User model."""

    def test_model_create(self):
        """A simple test to check model consistency."""

        UserFactory(username="Sam", email="sam@fun-test.fr", language="fr-fr")
        UserFactory(username="Joanie")

        self.assertEqual(User.objects.count(), 2)

        first_user = User.objects.first()
        self.assertEqual(first_user.username, "Sam")
        self.assertEqual(first_user.email, "sam@fun-test.fr")
        self.assertEqual(first_user.language, "fr-fr")
        self.assertEqual(str(first_user), "Sam")

    @override_settings(
        LANGUAGES=(("fr-ca", "Canadian"), ("it", "Italian")),
        LANGUAGE_CODE="fr-ca",
    )
    def test_model_create_language(self):
        """Check language is part of the languages
        declared in the settings."""

        UserFactory(username="Sam", email="sam@fun-test.fr", language="fr-ca")
        UserFactory(username="Sam2", email="sam@fun-test.fr", language="it")

        with self.assertRaises(ValidationError) as context:
            UserFactory(username="Sam3", email="sam@fun-test.fr", language="fr-fr")

        self.assertEqual(
            "La valeur « 'fr-fr' » n’est pas un choix valide.",
            str(context.exception.messages[0]),
        )

        with self.assertRaises(ValidationError):
            UserFactory(username="Sam", email="sam@fun-test.fr", language="en-us")

    def test_models_unique_username(self):
        """
        There should be a db constraint forcing uniqueness of username
        """
        UserFactory(username="Sam", email="sam@fun-test.fr")

        with self.assertRaises(ValidationError) as error:
            UserFactory(username="Sam")
            self.assertEqual(
                "{'username': ['A user with that username already exists.']}",
                str(error.exception),
            )

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
        self.assertEqual(user.language, "fr-fr")
        # no new object has been created
        self.assertEqual(User.objects.count(), 1)

        request.username = "Sam2"
        request.language = "en"
        User.update_or_create_from_request_user(request)
        # a new object has been created
        self.assertEqual(User.objects.count(), 2)
        user2 = User.objects.get(username="Sam2")
        self.assertEqual(user2.language, "en-us")
        self.assertEqual(user2.email, "sam@fun-test.fr")

    def test_models_create_or_update_from_request_language(self):
        """
        Check using the method create_or_update_from_request, the language
        is set depending of the values of the language available in the
        settings and understood in different ways
        """
        request = RequestFactory()
        request.username = "Sam"
        request.email = "sam@fun-test.fr"

        # with _
        request.language = "fr_FR"
        User.update_or_create_from_request_user(request)
        user = User.objects.get(username="Sam")
        user.refresh_from_db()
        self.assertEqual(user.language, "fr-fr")

        request.language = "en"
        User.update_or_create_from_request_user(request)
        user.refresh_from_db()
        self.assertEqual(user.language, "en-us")

        request.language = "en-gb"
        User.update_or_create_from_request_user(request)
        user.refresh_from_db()
        self.assertEqual(user.language, "en-us")

        request.language = "fr"
        User.update_or_create_from_request_user(request)
        user.refresh_from_db()
        self.assertEqual(user.language, "fr-fr")

        # `it` is not defined in the settings
        request.language = "it"
        User.update_or_create_from_request_user(request)
        user.refresh_from_db()
        # the default language is used
        self.assertEqual(user.language, "en-us")

        request.language = "whatever"
        User.update_or_create_from_request_user(request)
        user.refresh_from_db()
        # the default language is used
        self.assertEqual(user.language, "en-us")

        with override_settings(
            LANGUAGES=(("fr-ca", "Canadian"), ("it", "Italian"), ("es-ve", "Spain")),
            LANGUAGE_CODE="es-ve",
        ):
            request.language = "fr_FR"
            User.update_or_create_from_request_user(request)
            user.refresh_from_db()
            self.assertEqual(user.language, "fr-ca")

            request.language = "fr-FR"
            User.update_or_create_from_request_user(request)
            user.refresh_from_db()
            self.assertEqual(user.language, "fr-ca")

            request.language = "fr"
            User.update_or_create_from_request_user(request)
            user.refresh_from_db()
            self.assertEqual(user.language, "fr-ca")

            request.language = "it"
            User.update_or_create_from_request_user(request)
            user.refresh_from_db()
            self.assertEqual(user.language, "it")

            request.language = "ru"
            User.update_or_create_from_request_user(request)
            user.refresh_from_db()
            # default is used
            self.assertEqual(user.language, "es-ve")
