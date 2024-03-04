"""
Common base test cases
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import translation

from rest_framework_simplejwt.tokens import AccessToken

from joanie.core.utils.jwt_tokens import generate_jwt_token_from_user


class BaseAPITestCase(TestCase):
    """Base API test case"""

    def setUp(self):
        """
        We are testing in english
        """
        super().setUp()
        translation.activate("en-us")

    @staticmethod
    def get_user_token(username, expires_at=None):
        """
        Generate a jwt token used to authenticate a user

        Args:
            username: str, username to encode
            expires_at: datetime.datetime, time after which the token should expire.

        Returns:
            token, the jwt token generated as it should
        """
        issued_at = datetime.utcnow()
        token = AccessToken()
        token.payload.update(
            {
                "email": f"{username}@funmooc.fr",
                "exp": expires_at or issued_at + timedelta(days=2),
                "iat": issued_at,
                "language": settings.LANGUAGE_CODE,
                "username": username,
            }
        )
        return token

    @staticmethod
    def generate_token_from_user(user, expires_at=None):
        """
        Generate a jwt token used to authenticate a user from a user registered in
        the database

        Args:
            user: User
            expires_at: datetime.datetime, time after which the token should expire.

        Returns:
            token, the jwt token generated as it should
        """
        return generate_jwt_token_from_user(user, expires_at)


class BaseLogMixinTestCase:
    """Mixin for logging testing"""

    maxDiff = None

    def assertLogsEquals(self, records, expected_records):
        """Check that the logs are as expected

        Usage:
        Wrap the method you want to test with an assertLogs:
            with self.assertLogs("joanie") as logs:
                method_to_test()

        Check the logs by passing the logs.records and the expected logs:
            self.assertLogsEquals(logs.records, [
                ("INFO", "message", {"context_key": context_type}),
                ("ERROR", "message"),
            ])

        Each log is a tuple, with the level, the message and the context.
        The context is optional, and you can pass the type of the context key as a string.
        If you don't pass the context, it will not be checked.
        """
        try:
            self.assertEqual(len(records), len(expected_records))
        except AssertionError:
            if len(records) > len(expected_records):
                real_records = "\n".join(
                    [
                        f"{record.levelname} log from {record.pathname[5:]}:{record.lineno}"
                        for record in records
                    ]
                )
                raise AssertionError(
                    f"Too many logs were recorded: {len(records)} > {len(expected_records)} "
                    f"\n{real_records}"
                ) from None
            raise AssertionError(
                f"Too few logs were recorded: {len(records)} < {len(expected_records)}"
            ) from None

        for record, expected_record in zip(records, expected_records, strict=False):
            assert_failed_message = (
                f"{record.levelname}: {record.getMessage()} log from "
                f"{record.pathname[5:]}:{record.lineno} has wrong"
            )
            self.assertEqual(
                record.levelname, expected_record[0], f"{assert_failed_message} level"
            )
            self.assertEqual(
                record.getMessage(),
                expected_record[1],
                f"{assert_failed_message} message",
            )

            context = getattr(record, "context", None)
            try:
                expected_context = expected_record[2]
            except IndexError:
                # if no context is expected, we don't want to check it
                continue

            try:
                self.assertCountEqual(
                    context.keys(),
                    expected_context.keys(),
                    f"{assert_failed_message} context keys",
                )
            except AttributeError as error:
                raise AssertionError(
                    f"{assert_failed_message} context : is not a dict"
                ) from error
            for key, _type in expected_context.items():
                self.assertEqual(
                    type(context[key]),
                    _type,
                    f"{assert_failed_message} context key {key}",
                )
