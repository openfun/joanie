"""
Backend to connect Joanie to OpenEdX LMS
"""
import json
import logging
import re

import requests
from requests.auth import AuthBase

from backend.joanie.core.enums import ENROLLMENT_STATE_FAILED, ENROLLMENT_STATE_IN_PROGRESS, ENROLLMENT_STATE_VALIDATED

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)

"""
Passed states:
downloadable - The certificate is available for download.
generating   - A request has been made to generate a certificate, but it has not been generated yet.

Not passed states:
notpassing   - The student was graded but is not passing
"""
COURSE_RUN_CERTIFICATE_STATUS_DOWNLOADABLE = "downloadable"
COURSE_RUN_CERTIFICATE_STATUS_GENERATING = "generating"
COURSE_RUN_CERTIFICATE_STATUS_NOT_PASSING = "notpassing"
COURSE_RUN_PASSED_STATUSES = (COURSE_RUN_CERTIFICATE_STATUS_DOWNLOADABLE, COURSE_RUN_CERTIFICATE_STATUS_GENERATING)
COURSE_RUN_NOT_PASSED_STATUSES = (COURSE_RUN_CERTIFICATE_STATUS_NOT_PASSING)


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

    def _get_enrollment_state(status):
        if status in COURSE_RUN_NOT_PASSED_STATUSES:
            return ENROLLMENT_STATE_FAILED
        elif status in COURSE_RUN_PASSED_STATUSES:
            return ENROLLMENT_STATE_VALIDATED
        
        return ENROLLMENT_STATE_IN_PROGRESS

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
                return data

        logger.error(response.content)
        return None

    def get_progression(self, username, resource_link=None):
        """
            Get state of each course runs delivering a certificate
            to which user is enrolled. This is an easy way to retrieve the progression of an user
            about a course run.

            Return:
            [
                {
                    "course_key": "course-v1:edX+DemoX+Demo_Course",
                    "status": 
                          ENROLLMENT_STATE_IN_PROGRESS
                        | ENROLLMENT_STATE_VALIDATED
                        | ENROLLMENT_STATE_FAILED,
                    "grade": "0.98",
                }
            ]
        """
        base_url = self.configuration["BASE_URL"]

        # We ensure compatiblity with OpenEdX Dogwood by passing two query parameters
        # to send the username :
        # - `query` parameter is for OpenEdX Dogwood
        # - `user` parameter is for OpenEdX upper than Dogwood
        response = self.api_client.request(
            "GET", f"{base_url}/certificates/search?user={username}&query={username}"
        )

        if response.ok:
            results = [
                {
                    "course_key": result["course_key"],
                    "grade": result["grade"],
                    "status": self._get_enrollment_state(result["status"]),
                }
                for result
                in json.loads(response.content) if response.content else []
            ] 

            if resource_link:
                course_id = self.extract_course_id(resource_link)
                results = filter(lambda result: result.get("course_key", "") == course_id, results)

            return results
        
        logger.error(response.content)
        return None
