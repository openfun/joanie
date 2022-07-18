"""OpenBadgeFactory provider."""

import json
import logging
import re
from collections.abc import Iterable
from functools import cache
from typing import Literal, Optional
from urllib.parse import urljoin

# pylint: disable=no-name-in-module
import requests
from pydantic import (
    BaseModel,
    EmailStr,
    HttpUrl,
    NoneStr,
    ValidationError,
    root_validator,
)
from requests.exceptions import JSONDecodeError as RequestsJSONDecodeError

from ..exceptions import AuthenticationError, BadgeProviderError
from .base import BaseProvider

logger = logging.getLogger(__name__)


class OAuth2AccessToken(requests.auth.AuthBase):
    """Add OAuth2 access token to HTTP API requests header."""

    def __init__(self, access_token):
        """Instantiate requests Auth object with generated access_token."""

        self.access_token = access_token

    def __call__(self, request):
        """Modify and return the request."""

        request.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
            }
        )

        return request


class OBFAPIClient(requests.Session):
    """Open Badge Factory API Client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *args,
        raise_for_status: bool = False,
        **kwargs,
    ):
        """Override default requests.Session instantiation to handle authentication."""

        super().__init__(*args, **kwargs)

        self.api_root_url: str = "https://openbadgefactory.com"
        self.api_version_prefix: str = "v1"
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.raise_for_status: bool = raise_for_status
        self.auth = self._get_auth
        self.headers.update(
            {
                "Content-Type": "application/json",
            }
        )

    @staticmethod
    @cache
    def _access_token(
        client_id: str, client_secret: str, api_version_prefix: str, api_root_url: str
    ):
        """Request OAuth2 access token from the API backend.

        We cache this function to avoid regenerating an access token at each
        API request. This access token has a limited validity (e.g. 10h) so we
        try to regenerate it when the API response code is 403 (see the
        `request` overridden method).

        """

        url = f"{api_version_prefix}/client/oauth2/token"
        response = requests.post(
            urljoin(api_root_url, url),
            json={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        try:
            json_response = response.json()
        except RequestsJSONDecodeError as exc:
            raise AuthenticationError(
                "Invalid response from the OBF server with provided credentials"
            ) from exc

        if "access_token" not in json_response:
            raise AuthenticationError(
                "Cannot get an access token from the OBF server with provided credentials"
            )

        return json_response.get("access_token")

    @property
    def _get_auth(self):
        """Make access token generation dynamic."""

        return OAuth2AccessToken(
            self._access_token(
                self.client_id,
                self.client_secret,
                self.api_version_prefix,
                self.api_root_url,
            )
        )

    def check_auth(self):
        """Check OBF API credentials using the dedicated endpoint."""

        url = f"/ping/{self.client_id}"
        response = self.get(url)
        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise AuthenticationError("Invalid access token for OBF")
        return response

    @classmethod
    def iter_json(cls, response: requests.Response) -> Iterable:
        """Iterate over JSON lines serialization in API responses.

        When multiple objects are returned by the API, they are streamed as
        JSON lines instead of a JSON list, leading the response.json() method
        to fail as it is expected a valid JSON list instead. We mitigate this
        issue by forcing JSON serialization of each item in the response.
        """

        try:
            json_response = response.json()
            if isinstance(json_response, list):
                yield from json_response
            else:
                yield json_response
        except requests.JSONDecodeError:
            for line in response.iter_lines():
                yield json.loads(line)

    # pylint: disable=arguments-differ
    def request(self, method, url, **kwargs):
        """Make OBF API usage more developer-friendly:

        - Automatically add the API root URL so that we can focus on the endpoints
        - Automatically renew access token when expired
        """

        url = urljoin(self.api_root_url, f"{self.api_version_prefix}/{url}")
        response = super().request(method, url, **kwargs)

        # Try to regenerate the access token in case of 403 response
        if (
            response.status_code
            == requests.codes.forbidden  # pylint: disable=no-member
        ):
            # Clear cached property and force access token update
            self._access_token.cache_clear()
            self.auth = self._get_auth
            # Give it another try
            return super().request(method, url, **kwargs)

        # Check response status and raise an exception on error
        if self.raise_for_status:
            response.raise_for_status()

        return response


class Badge(BaseModel):
    """Open Badge Factory Badge Model."""

    id: NoneStr = None
    name: str
    description: str
    draft: bool = False
    image: NoneStr = None
    css: NoneStr = None
    criteria_html: NoneStr = None
    email_subject: NoneStr = None
    email_body: NoneStr = None
    email_link_text: NoneStr = None
    email_footer: NoneStr = None
    expires: Optional[int] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None
    is_created: bool = False

    # pylint: disable=no-self-argument
    @root_validator
    def check_id(cls, values):
        """Created badges (fetched from the API) should have an identifier."""

        id_ = values.get("id")
        is_created = values.get("is_created")

        if is_created and id_ is None:
            raise ValidationError("Created badges should have an `id` field.")

        return values


class BadgeQuery(BaseModel):
    """Open Badge Factory badge query filters."""

    draft: Optional[Literal[0, 1]] = None
    category: Optional[list[str]] = None
    id: Optional[list[str]] = None
    query: NoneStr = None
    meta: Optional[dict] = None
    external: Optional[Literal[0, 1]] = None

    def params(self):
        """Convert model to OBF badge query parameters."""

        query = self.dict()
        if query.get("category", None) is not None:
            query["category"] = "|".join(query.get("category"))
        if query.get("id", None) is not None:
            query["id"] = "|".join(query.get("id"))
        if query.get("meta", None) is not None:
            for key in query["meta"]:
                query[f"meta:{key}"] = query["meta"][key]
            del query["meta"]

        return query


class IssueBadgeOverride(BaseModel):
    """Open Badge Factory issue badge override model."""

    name: NoneStr = None
    description: NoneStr = None
    tags: Optional[list[str]] = None
    criteria: NoneStr = None
    criteria_add: NoneStr = None


class BadgeIssue(BaseModel):
    """Open Badge Factory badge issue Model."""

    recipient: list[EmailStr]
    expires: Optional[int] = None
    issued_on: Optional[int] = None
    email_subject: NoneStr = None
    email_body: NoneStr = None
    email_link_text: NoneStr = None
    email_footer: NoneStr = None
    badge_override: Optional[IssueBadgeOverride] = None
    log_entry: Optional[dict] = None
    api_consumer_id: NoneStr = None
    send_email: Literal[0, 1] = 1


class BadgeRevokation(BaseModel):
    """Open Badge Factory badge revokation model."""

    event_id: str
    recipient: list[EmailStr]

    def params(self):
        """Convert recipient list to a pipe-separated list."""

        return {"email": "|".join(self.recipient)}


class OBF(BaseProvider):
    """Open Badge Factory provider.

    API documentation:
    https://openbadgefactory.com/static/doc/obf-api-v1.pdf
    """

    code: str = "OBF"
    name: str = "Open Badge Factory"

    def __init__(
        self, client_id: str, client_secret: str, raise_for_status: bool = False
    ):
        """Initialize the API client."""

        super().__init__()
        self.api_client = OBFAPIClient(
            client_id, client_secret, raise_for_status=raise_for_status
        )

    def create(self, badge: Badge) -> Badge:
        """Create a badge."""

        response = self.api_client.post(
            f"/badge/{self.api_client.client_id}", json=badge.dict()
        )
        if (
            not response.status_code
            == requests.codes.created  # pylint: disable=no-member
        ):
            raise BadgeProviderError(f"Cannot create badge: {badge}")

        # Get badge ID
        badge_url = response.headers.get("Location")
        badge.id = re.match(
            f"/v1/badge/{self.api_client.client_id}/(.*)", badge_url  # type: ignore
        ).groups()[0]

        # Get created badge
        fetched = next(self.read(badge=badge))  # type: ignore
        fetched.is_created = True
        logger.info("Successfully created badge '%s' with ID: %s", badge.name, badge.id)

        return Badge(**fetched.dict())

    def read(self, badge: Badge = None, query: BadgeQuery = None) -> Iterable[Badge]:
        """Fetch one, selected or all badges.

        Args:
            badge: if provided will only yield selected badge (using the badge id)
            query: select badges and yield them

        If no `badge` or `query` argument is provided, it yields all badges.
        """

        # Get a single badge
        if badge is not None:
            if badge.id is None:
                raise BadgeProviderError(
                    "We expect an existing badge instance (the ID field is required)"
                )
            response = self.api_client.get(
                f"/badge/{self.api_client.client_id}/{badge.id}"
            )
            logger.info("Successfully get badge with ID: %s", badge.id)

        # Get a selected badge list
        elif query is not None:
            response = self.api_client.get(
                f"/badge/{self.api_client.client_id}",
                params=query.params(),
            )
            logger.info("Successfully filtered badges from query")

        # Get all badges list
        else:
            response = self.api_client.get(
                f"/badge/{self.api_client.client_id}",
            )
            logger.info("Successfully listed badges")

        for item in self.api_client.iter_json(response):
            yield Badge(**item, is_created=True)

    def update(self, badge: Badge) -> Badge:
        """Update a badge."""

        if badge.id is None:
            raise BadgeProviderError(
                "We expect an existing badge instance (the ID field is required)"
            )

        response = self.api_client.put(
            f"/badge/{self.api_client.client_id}/{badge.id}", json=badge.dict()
        )
        if (
            not response.status_code
            == requests.codes.no_content  # pylint: disable=no-member
        ):
            raise BadgeProviderError(f"Cannot update badge with ID: {badge.id}")
        logger.info("Successfully updated badge '%s' with ID: %s", badge.name, badge.id)

        return badge

    def delete(self, badge: Badge = None) -> None:
        """Delete a badge."""

        # Delete all client badges
        if badge is None:
            logger.critical("Will delete all client badges!")
            response = self.api_client.delete(f"/badge/{self.api_client.client_id}")
            if (
                not response.status_code
                == requests.codes.no_content  # pylint: disable=no-member
            ):
                raise BadgeProviderError(
                    f"Cannot delete badges for client with ID: {self.api_client.client_id}"
                )
            logger.info(
                "All badges have been deleted for the '%s' client",
                self.api_client.client_id,
            )
            return

        if badge.id is None:
            raise BadgeProviderError(
                "We expect an existing badge instance (the ID field is required)"
            )

        # Delete a single badge
        logger.critical("Will delete badge '%s' with ID: %s", badge.name, badge.id)
        response = self.api_client.delete(
            f"/badge/{self.api_client.client_id}/{badge.id}"
        )
        if (
            not response.status_code
            == requests.codes.no_content  # pylint: disable=no-member
        ):
            raise BadgeProviderError(f"Cannot delete badge with ID: {badge.id}")
        logger.critical("Deleted badge '%s' with ID: %s", badge.name, badge.id)

    def issue(self, badge: Badge, issue: BadgeIssue) -> tuple[HttpUrl, str]:
        """Issue a badge and return issuing event URL and ID.

        Note that you cannot issue a badge with a draft status.
        """

        if badge.id is None:
            raise BadgeProviderError(
                "We expect an existing badge instance (the ID field is required)"
            )
        if badge.draft:
            raise BadgeProviderError(
                f"You cannot issue a badge with a draft status (ID: {badge.id})"
            )

        response = self.api_client.post(
            f"/badge/{self.api_client.client_id}/{badge.id}", json=issue.dict()
        )
        if (
            not response.status_code
            == requests.codes.created  # pylint: disable=no-member
        ):
            raise BadgeProviderError(f"Cannot issue badge with ID: {badge.id}")

        event_url = response.headers.get("Location")
        logger.info(
            "Successfully issued %d badges for badge ID: %s",
            len(issue.recipient),
            badge.id,
        )
        logger.info("Issued badges event URL: %s", event_url)
        event_id = re.match(
            f"/v1/event/{self.api_client.client_id}/(.*)", event_url  # type: ignore
        ).groups()[0]

        return event_url, event_id  # type: ignore

    def revoke(self, revokation: BadgeRevokation) -> None:
        """Revoke one or more issued badges."""

        logger.warning("Will revoke event: %s", revokation)
        response = self.api_client.delete(
            f"/event/{self.api_client.client_id}/{revokation.event_id}",
            params=revokation.params(),
        )
        if (
            not response.status_code
            == requests.codes.no_content  # pylint: disable=no-member
        ):
            raise BadgeProviderError(f"Cannot revoke event: {revokation}")
        logger.info("Revoked event: %s", revokation)
