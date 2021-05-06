"""
Specific exceptions for the core application
"""


class EnrollmentError(Exception):
    """An exception to raise if an enrollment fails."""


class InvalidCourseRuns(Exception):
    """
    Exception raised when course runs selected for a product order mismatch with course runs
    available for the product.
    """
