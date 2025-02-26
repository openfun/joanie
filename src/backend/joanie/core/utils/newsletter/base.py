"""Base Newsletter Client"""

import logging

logger = logging.getLogger(__name__)


class NewsletterClient:
    """
    Base class for newsletter clients.
    All newsletter clients should inherit from this class.
    """

    name = "NewsletterClient"

    def __init__(self, user):
        self._validate_class_attributes()
        self.user = user or {}
        self.logger = logger

    def _validate_class_attributes(self):
        """
        Validate the class attributes.
        """
        if self.list_id is None:
            raise NotImplementedError("list_id must be defined in child classes")

    def _log_info(self, message):
        """Log an info message."""
        self.logger.info(message, self.user.get("id"), self.list_id)

    def _check_response_api(self, response, log_level):
        """
        Check the response from the API.
        """
        if not response.ok:
            self.logger.log(
                log_level,
                "Error calling %s API %s | %s: %s",
                self.name,
                response.url,
                response.status_code,
                response.text,
                extra={
                    "context": {
                        "user_id": self.user.get("id"),
                        "list_id": self.list_id,
                        "url": response.url,
                        "response": response.text,
                    }
                },
            )

        return response

    def subscribe_to_commercial_list(self):
        """
        Add a contact to the commercial newsletter list.
        """
        raise NotImplementedError("This method should be implemented by the subclass.")

    def unsubscribe_from_commercial_list(self):
        """
        Remove a contact from the commercial newsletter list.
        """
        raise NotImplementedError("This method should be implemented by the subclass.")
