"""Utility class to create a Billing Address object for a company"""

from dataclasses import dataclass


@dataclass
class CompanyBillingAddress:
    """Small class to create company billing address for payments"""

    address: str
    postcode: str
    city: str
    country: str
    language: str
    first_name: str  # The fullname is in `first_name` field in Joanie
    last_name: str = ""
