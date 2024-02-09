"""Base test case for the migrate command."""
from django.test import TestCase, override_settings

from joanie.edx_imports.edx_factories import session


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    },
    JOANIE_LMS_BACKENDS=[
        {
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        }
    ],
    EDX_DATABASE_USER="test",
    EDX_DATABASE_PASSWORD="test",
    EDX_DATABASE_HOST="test",
    EDX_DATABASE_PORT="1234",
    EDX_DATABASE_NAME="test",
    EDX_DOMAIN="openedx.test",
    EDX_SECRET="test",
    EDX_TIME_ZONE="UTC",
    TIME_ZONE="UTC",
)
class MigrateOpenEdxBaseTestCase(TestCase):
    """Base test case for the migrate command."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        session.rollback()

    def assertLogsContains(self, logger, expected_records):
        """
        Assert that the logger contains the expected messages and levels.
        """
        records = [record.getMessage() for record in logger.records]
        for expected_record in expected_records:
            is_found = False
            for record in records:
                try:
                    self.assertIn(expected_record, record)
                    is_found = True
                    break
                except AssertionError:
                    pass
            if not is_found:
                self.fail(f"Expected record {expected_record} not found in {records}")
