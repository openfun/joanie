"""Badge provider interface."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Base badge provider class."""

    code: str = "BPC"
    name: str = "Base provider"

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """Initialize the API client."""

    @abstractmethod
    def create(self, badge):
        """Create a badge."""

    @abstractmethod
    def read(self, badge=None, query=None):
        """Read a badge."""

    @abstractmethod
    def update(self, badge):
        """Update a badge."""

    @abstractmethod
    def delete(self, badge=None):
        """Delete a badge."""

    @abstractmethod
    def issue(self, badge, issue):
        """Issue a badge."""

    @abstractmethod
    def revoke(self, revokation):
        """Revoke one or more badges."""
