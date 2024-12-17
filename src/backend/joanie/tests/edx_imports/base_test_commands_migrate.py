"""Base test case for the migrate command."""

from django.test import override_settings

from joanie.edx_imports.edx_factories import session
from joanie.tests.base import LoggingTestCase


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
class MigrateOpenEdxBaseTestCase(LoggingTestCase):
    """Base test case for the migrate command."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        session.rollback()
