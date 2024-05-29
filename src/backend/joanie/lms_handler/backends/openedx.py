"""
Backend to connect Joanie to OpenEdX LMS
"""

import json
import logging
import re

from django.db.models import Q

import requests
from requests.auth import AuthBase
from requests.exceptions import RequestException

from joanie.core import enums
from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.core.models.products import Order
from joanie.lms_handler.backends.base import BaseLMSBackend
from joanie.lms_handler.serializers import SyncCourseRunSerializer

logger = logging.getLogger(__name__)


OPENEDX_MODE_HONOR = "honor"
OPENEDX_MODE_VERIFIED = "verified"


def split_course_key(key):
    """Split an OpenEdX course key by organization, course and course run codes.

    We first try splitting the key as a version 1 key (course-v1:org+course+run)
    and fallback the old version (org/course/run).
    """
    if key.startswith("course-v1:"):
        organization, course, run = key[10:].split("+")
    else:
        organization, course, run = key.split("/")

    return organization, course, run


class OpenEdXTokenAuth(AuthBase):
    """Attach HTTP token authentication header to the given Request object."""

    def __init__(self, token):
        """Set-up token value in the instance."""
        self.token = token

    def __call__(self, request):
        """Modify and return the request."""
        request.headers.update(
            {
                "Content-Type": "application/json",
                "X-Edx-Api-Key": self.token,
            }
        )

        return request


class TokenAPIClient(requests.Session):
    """
    A class `request.Session` that automatically authenticates against OpenEdX's preferred
    authentication method up to Dogwood, given a secret token.

    For more usage details, see documentation of the class `requests.Session` object:
    https://requests.readthedocs.io/en/master/user/advanced/#session-objects
    """

    def __init__(self, token, *args, **kwargs):
        """Extending the session object by setting the authentication token."""
        super().__init__(*args, **kwargs)
        self.auth = OpenEdXTokenAuth(token)


class OpenEdXLMSBackend(BaseLMSBackend):
    """LMS backend for Joanie tested with Open EdX Dogwood, Hawthorn and Ironwood."""

    @property
    def api_client(self):
        """Instantiate and return an OpenEdX token API client."""
        return TokenAPIClient(self.configuration["API_TOKEN"])

    def extract_course_id(self, resource_link):
        """Extract the LMS course id from the course run url."""
        return re.match(self.configuration["COURSE_REGEX"], resource_link).group(
            "course_id"
        )

    def get_enrollment(self, username, resource_link):
        """Get enrollment status for a user on a course run given its url"""
        base_url = self.configuration["BASE_URL"]
        course_id = self.extract_course_id(resource_link)
        try:
            response = self.api_client.request(
                "GET",
                f"{base_url}/api/enrollment/v1/enrollment/{username},{course_id}",
            )
        except RequestException as exc:
            logger.error(exc)
            return None

        if response.ok:
            return json.loads(response.content) if response.content else {}

        logger.error(response.content)
        return None

    def _needs_update(self, enrollment, target_mode):
        """
        Return True if the enrollment needs to be updated on the remote LMS.
        An enrollment must be updated if its active status or mode has changed.
        """
        enrollment_state = self.get_enrollment(
            enrollment.user.username, enrollment.course_run.resource_link
        )

        if not enrollment_state:
            return True

        has_active_changed = enrollment_state.get("is_active") != enrollment.is_active
        has_mode_changed = enrollment_state.get("mode") != target_mode
        return has_active_changed or has_mode_changed

    def set_enrollment(self, enrollment):
        """Set enrollment for a user on the remote LMS using resource link as url."""
        base_url = self.configuration["BASE_URL"]
        course_id = self.extract_course_id(enrollment.course_run.resource_link)
        mode = (
            OPENEDX_MODE_VERIFIED
            if Order.objects.filter(
                Q(target_courses=enrollment.course_run.course)
                | Q(enrollment=enrollment),
                # TODO: change to:
                #  state__in=[
                #      enums.ORDER_STATE_COMPLETED,
                #      enums.ORDER_STATE_PENDING_PAYMENT,
                #      enums.ORDER_STATE_FAILED_PAYMENT
                #  ],
                #  https://github.com/openfun/joanie/pull/801#discussion_r1618650542
                state=enums.ORDER_STATE_COMPLETED,
                owner=enrollment.user,
            ).exists()
            else OPENEDX_MODE_HONOR
        )

        if not self._needs_update(enrollment, mode):
            return

        payload = {
            "is_active": enrollment.is_active,
            "mode": mode,
            "user": enrollment.user.username,
            "course_details": {"course_id": course_id},
        }
        url = f"{base_url}/api/enrollment/v1/enrollment"
        try:
            response = self.api_client.request("POST", url, json=payload)
        except RequestException as exc:
            logger.error(exc)
            raise EnrollmentError() from exc

        if response.ok:
            data = json.loads(response.content)
            if data["is_active"] == enrollment.is_active:
                return

        logger.error(response.content)
        raise EnrollmentError()

    def get_grades(self, username, resource_link):
        """Get user's grades for a course run given its url."""
        base_url = self.configuration["BASE_URL"]
        course_id = self.extract_course_id(resource_link)
        url = f"{base_url}/fun/api/grades/{course_id}/{username}"
        try:
            response = self.api_client.request("GET", url)
        except RequestException as exc:
            logger.error(exc)
            raise GradeError() from exc

        if response.ok:
            return json.loads(response.content)

        logger.error(response.content)
        raise GradeError()

    def extract_course_number(self, data):
        """Extract the LMS course number from data dictionary."""
        course_id = self.extract_course_id(data.get("resource_link"))
        return split_course_key(course_id)[1]

    def clean_course_run_data(self, data):
        """Remove course run's protected fields to the data dictionary."""
        return {
            key: value
            for (key, value) in data.items()
            if key not in self.configuration.get("COURSE_RUN_SYNC_NO_UPDATE_FIELDS", [])
        }

    @staticmethod
    def get_course_run_serializer(data, partial=False):
        """Prepare data and return a bound serializer."""
        return SyncCourseRunSerializer(data=data, partial=partial)
