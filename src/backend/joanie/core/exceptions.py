"""
Specific exceptions for the core application
"""


class EnrollmentError(Exception):
    """An exception to raise if an enrollment fails."""


class GradeError(Exception):
    """An exception to raise when grade processing fails."""


class InvalidCourseRuns(Exception):
    """
    Exception raised when course runs selected for a product order mismatch with course runs
    available for the product.
    """


class NoContractToSignError(Exception):
    """
    Exception raised when trying to bulk sign organization contracts but no contract is available.
    """


class CertificateGenerationError(Exception):
    """
    Exception raised when the certificate generation process fails due to the order not meeting
    all specified conditions.
    """


class BackendTimeOut(Exception):
    """
    Exception raised when a backend reaches the timeout set when we are waiting
    for the response in return.
    """
