"""get_country_calendar() test suite"""

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from workalendar.europe import France

from joanie.payment import get_country_calendar


class GetCountryCalendarTestSuite(TestCase):
    """Test suite for the get_country_calendar method"""

    @override_settings(
        JOANIE_CALENDAR=None,
    )
    def test_get_country_calendar_when_setting_variable_is_misconfigured(self):
        """
        When `JOANIE_CONTRACT_COUNTRY_CALENDAR` is set with None in the settings,
        it raise a `ImproperlyConfigured` mentioning the issue.
        """
        with self.assertRaises(ImproperlyConfigured) as context:
            get_country_calendar()

        self.assertEqual(
            str(context.exception),
            "Cannot instantiate a calendar. "
            '`JOANIE_CONTRACT_COUNTRY_CALENDAR="None"` configuration seems not valid. '
            "Check your settings.py",
        )

    @override_settings(
        JOANIE_CALENDAR="workalendar.europe.Tothemoon",
    )
    def test_get_country_calendar_with_an_error_in_the_path_when_selecting_the_calendar(
        self,
    ):
        """
        When `JOANIE_CONTRACT_COUNTRY_CALENDAR` is misconfigured with a path
        that does not exist within the library's list of available calendars,
        it should raise a `ImproperlyConfigured` error.
        """
        with self.assertRaises(ImproperlyConfigured) as context:
            get_country_calendar()

        self.assertEqual(
            str(context.exception),
            "Cannot instantiate a calendar. "
            '`JOANIE_CONTRACT_COUNTRY_CALENDAR="workalendar.europe.Tothemoon"` '
            "configuration seems not valid. Check your settings.py",
        )

    @override_settings(
        JOANIE_CALENDAR="workalendar.europe.France",
    )
    def test_get_country_calendar_get_instantiate_object(self):
        """
        When `JOANIE_CONTRACT_COUNTRY_CALENDAR` is well configured,
        the country calendar should appear and should be the one for France for this test.
        """
        calendar = get_country_calendar()

        self.assertIsInstance(calendar, France)
        self.assertEqual(calendar.name, "France")
