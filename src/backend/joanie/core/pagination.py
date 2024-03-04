"""Pagination used by django rest framework."""

from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    """Pagination to display no more than 100 objects per page sorted by creation date."""

    ordering = "-created_on"
    max_page_size = 100
    page_size_query_param = "page_size"
