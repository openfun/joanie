"""Test suite for badge models."""

from django.core.exceptions import ValidationError
from django.test.utils import override_settings

from joanie.core import factories, models
from joanie.core.models import User
from joanie.tests.base import BaseAPITestCase


class UserModelTestCase(BaseAPITestCase):
    """Test suite for the User model."""

    def test_models_user_create(self):
        """A simple test to check model consistency."""

        factories.UserFactory(username="Sam", email="sam@fun-test.fr", language="fr-fr")
        factories.UserFactory(username="Joanie")

        self.assertEqual(models.User.objects.count(), 2)

        user = models.User.objects.get(username="Sam")
        self.assertEqual(user.username, "Sam")
        self.assertEqual(user.email, "sam@fun-test.fr")
        self.assertEqual(user.language, "fr-fr")
        self.assertEqual(str(user), "Sam")

    @override_settings(
        LANGUAGES=(("fr-ca", "Canadian"), ("it", "Italian")),
        LANGUAGE_CODE="fr-ca",
    )
    def test_models_user_create_language(self):
        """Check language is part of the languages
        declared in the settings."""

        factories.UserFactory(username="Sam", email="sam@fun-test.fr", language="fr-ca")
        factories.UserFactory(username="Sam2", email="sam@fun-test.fr", language="it")

        with self.assertRaises(ValidationError) as context:
            factories.UserFactory(
                username="Sam3", email="sam@fun-test.fr", language="fr-fr"
            )

        self.assertEqual(
            "La valeur « 'fr-fr' » n’est pas un choix valide.",
            str(context.exception.messages[0]),
        )

        with self.assertRaises(ValidationError):
            User.objects.create(
                username="Sam", email="sam@fun-test.fr", language="en-us"
            )

    def test_models_user_unique_username(self):
        """
        There should be a db constraint forcing uniqueness of username
        """
        factories.UserFactory(username="Sam", email="sam@fun-test.fr")

        with self.assertRaises(ValidationError) as error:
            User.objects.create(username="Sam")
            self.assertEqual(
                "{'username': ['A user with that username already exists.']}",
                str(error.exception),
            )

    def test_models_user_multiple_emails(self):
        """
        Multiple users can have the same email
        """
        factories.UserFactory(username="Sam", email="mail@fun-test.fr")
        factories.UserFactory(username="Joanie", email="mail@fun-test.fr")
        self.assertEqual(
            models.User.objects.filter(email="mail@fun-test.fr").count(), 2
        )

    def test_models_user_create_or_update_from_request_changed(self):
        """
        Check that, using the method `update_from_token`, the user
        values are updated as expected.
        """
        user = factories.UserFactory()

        new_user_for_data = factories.UserFactory.build()
        token = self.generate_token_from_user(new_user_for_data)

        with self.assertNumQueries(1):
            user.update_from_token(token)

        user.refresh_from_db()
        # user has been updated
        self.assertNotEqual(user.username, new_user_for_data.username)
        self.assertEqual(user.email, new_user_for_data.email)
        self.assertEqual(user.language, new_user_for_data.language)
        self.assertEqual(user.first_name, new_user_for_data.first_name)

        # no new object has been created
        self.assertEqual(models.User.objects.count(), 1)

    def test_models_user_create_or_update_from_request_unchanged(self):
        """
        Check that, using the method `update_from_token`, the user is not
        updated if no values have changed.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            user.update_from_token(token)

    def test_models_user_create_or_update_from_request_language(self):
        """
        Check that, using the method `update_from_token`, the language
        is set depending on the values of the language available in the
        settings and understood in different ways.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        token["language"] = "fr_FR"
        user.update_from_token(token)
        user.refresh_from_db()
        self.assertEqual(user.language, "fr-FR")

        token["language"] = "en"
        user.update_from_token(token)
        user.refresh_from_db()
        self.assertEqual(user.language, "en-us")

        token["language"] = "en-gb"
        user.update_from_token(token)
        user.refresh_from_db()
        self.assertEqual(user.language, "en-us")

        token["language"] = "fr"
        user.update_from_token(token)
        user.refresh_from_db()
        self.assertEqual(user.language, "fr-fr")

        # `it` is not defined in the settings
        token["language"] = "it"
        user.update_from_token(token)
        user.refresh_from_db()
        # the default language is used
        self.assertEqual(user.language, "en-us")

        token["language"] = "whatever"
        user.update_from_token(token)
        user.refresh_from_db()
        # the default language is used
        self.assertEqual(user.language, "en-us")

        with override_settings(
            LANGUAGES=(("fr-ca", "Canadian"), ("it", "Italian"), ("es-ve", "Spain")),
            LANGUAGE_CODE="es-ve",
        ):
            token["language"] = "fr_FR"
            user.update_from_token(token)
            user.refresh_from_db()
            self.assertEqual(user.language, "fr-ca")

            token["language"] = "fr"
            user.update_from_token(token)
            user.refresh_from_db()
            self.assertEqual(user.language, "fr-ca")

            token["language"] = "it"
            user.update_from_token(token)
            user.refresh_from_db()
            self.assertEqual(user.language, "it")

            token["language"] = "ru"
            user.update_from_token(token)
            user.refresh_from_db()
            # the default language is used
            self.assertEqual(user.language, "es-ve")

    # get_abilities

    def test_models_user_get_abilities_course_roles(self):
        """Check abilities returned for a user with roles on some courses."""
        user = factories.UserFactory()
        factories.CourseFactory(users=[(user, "manager")])
        factories.CourseFactory(users=[(user, "administrator")])
        factories.CourseFactory(users=[(user, "administrator")])

        with self.assertNumQueries(2):
            abilities = user.get_abilities(user)

        self.assertTrue(abilities["has_course_access"])
        self.assertFalse(abilities["has_organization_access"])

    def test_models_user_get_abilities_organization_roles(self):
        """Check abilities returned for a user with roles on some organizations."""
        user = factories.UserFactory()
        factories.OrganizationFactory(users=[(user, "member")])
        factories.OrganizationFactory(users=[(user, "administrator")])
        factories.OrganizationFactory(users=[(user, "administrator")])

        with self.assertNumQueries(2):
            abilities = user.get_abilities(user)

        self.assertFalse(abilities["has_course_access"])
        self.assertTrue(abilities["has_organization_access"])

    def test_models_user_get_other_user_abilities_organization_access(self):
        """
        Check abilities returned for a user other than self with
        roles on some organizations.
        """
        user = factories.UserFactory()
        user_target = factories.UserFactory()
        factories.OrganizationFactory(users=[(user_target, "member")])
        factories.OrganizationFactory(users=[(user_target, "administrator")])
        factories.OrganizationFactory(users=[(user_target, "administrator")])

        with self.assertNumQueries(2):
            abilities = user.get_abilities(user_target)

        self.assertFalse(abilities["has_course_access"])
        self.assertTrue(abilities["has_organization_access"])

    def test_models_user_get_other_user_abilities_course_access(self):
        """
        Check abilities returned for a user other than self with
        roles on some courses.
        """
        user = factories.UserFactory()
        user_target = factories.UserFactory()
        factories.CourseFactory(users=[(user_target, "manager")])
        factories.CourseFactory(users=[(user_target, "administrator")])
        factories.CourseFactory(users=[(user_target, "administrator")])

        with self.assertNumQueries(2):
            abilities = user.get_abilities(user_target)

        self.assertTrue(abilities["has_course_access"])
        self.assertFalse(abilities["has_organization_access"])

    def test_models_user_field_phone_number_formatted(self):
        """The `phone_number` field should be formatted without spaces on save."""
        user1 = factories.UserFactory(phone_number="00 11 1 23 45 67 89")
        user1.save()

        self.assertEqual(user1.phone_number, "0011123456789")

        user2 = factories.UserFactory(phone_number="01 23 45 67 89")
        user2.save()

        self.assertEqual(user2.phone_number, "0123456789")

    def test_models_user_field_phone_number_special_characters_normalized(
        self,
    ):
        """
        The `phone_number` field should be normalized without non-digits and spaces on save.
        The field should only include digits and '+' characters.
        """
        user = factories.UserFactory(phone_number="+1 (123) 123-4567")
        user.save()

        self.assertEqual(user.phone_number, "+11231234567")

        user2 = factories.UserFactory(phone_number="+(33) 1 23 45 67 89")
        user2.save()

        self.assertEqual(user2.phone_number, "+33123456789")

    def test_models_user_field_phone_number_empty(self):
        """The `phone_number` field should remain empty if initially empty."""
        user = factories.UserFactory(phone_number="")
        user.save()

        self.assertEqual(user.phone_number, "")

    def test_models_user_field_phone_number_no_digits(self):
        """The `phone_number` field should be empty if no digits are provided."""
        user = factories.UserFactory(phone_number="abc wrong number")
        user.save()

        self.assertEqual(user.phone_number, "")
