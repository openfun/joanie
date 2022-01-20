"""
Base Backend to connect Joanie to a LMS
"""


class BaseLMSBackend:
    """
    Base backend to hold all LMS common methods and provide a skeleton for others.
    """

    def __init__(self, configuration, *args, **kwargs):
        """Attach configuration to the LMS backend instance."""
        super().__init__(*args, **kwargs)
        self.configuration = configuration

    def get_enrollment(self, username, resource_link):
        """Retrieve an enrollment according to a username and a resource_link."""
        raise NotImplementedError(
            "subclasses of BaseLMSBackend must provide a get_enrollment() method"
        )

    def set_enrollment(self, username, resource_link, active=True):
        """Activate/deactivate an enrollment according to a username and a resource_link."""
        raise NotImplementedError(
            "subclasses of BaseLMSBackend must provide a set_enrollment() method"
        )

    def get_grades(self, username, resource_link):
        """Get user's grades for a course run given its url."""
        raise NotImplementedError(
            "subclasses of BaseLMSBackend must provide a get_grades() method"
        )
