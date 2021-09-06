"""
Backend to connect Joanie to OpenEdX LMS
"""
import json
import logging
import re

import requests
from requests.auth import AuthBase

from joanie.core.exceptions import EnrollmentError
from joanie.lms_handler.serializers import SyncCourseRunSerializer

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)


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
        response = self.api_client.request(
            "GET",
            f"{base_url}/api/enrollment/v1/enrollment/{username},{course_id}",
        )

        if response.ok:
            return json.loads(response.content) if response.content else {}

        logger.error(response.content)
        return None

    def set_enrollment(self, username, resource_link, active=True):
        """Set enrollment for a user with a course run given its url."""
        base_url = self.configuration["BASE_URL"]
        course_id = self.extract_course_id(resource_link)
        payload = {
            "is_active": active,
            "user": username,
            "course_details": {"course_id": course_id},
        }
        url = f"{base_url}/api/enrollment/v1/enrollment"
        response = self.api_client.request("POST", url, json=payload)

        if response.ok:
            data = json.loads(response.content)
            if data["is_active"] == active:
                return

        logger.error(response.content)
        raise EnrollmentError()

    def extract_course_number(self, data):
        """Extract the LMS course number from data dictionary."""
        course_id = self.extract_course_id(data.get("resource_link"))
        return split_course_key(course_id)[1]

    def clean_course_run_data(self, data):
        """Remove course run's protected fields to the data dictionnary."""
        return {
            key: value
            for (key, value) in data.items()
            if key not in self.configuration.get("COURSE_RUN_SYNC_NO_UPDATE_FIELDS", [])
        }

    @staticmethod
    def get_course_run_serializer(data, partial=False):
        """Prepare data and return a bound serializer."""
        return SyncCourseRunSerializer(data=data, partial=partial)
