"""
Specific exceptions for the core application
"""


class OrderAlreadyExists(Exception):
    """
    Exception raised when we try to create more than one valid order for the same product and user.
    """


class InvalidCourseRuns(Exception):
    """
    Exception raised when course runs selected for a product order mismatch with course runs
    available for the product.
    """
