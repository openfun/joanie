"""
Remote endpoints API for other servers.
"""
from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response

from joanie.core.permissions import HasAPIKey
from joanie.core.utils.course_run import get_course_run_metrics


@api_view(["GET"])
@permission_classes([HasAPIKey])
@authentication_classes([])
def enrollments_and_orders_on_course_run(request: Request):
    """
    If the related course run is archived, return the amount of active enrollments and the amount
    of validated certificate orders.
    It requires an existing `resource_link` from an ended course run as input.

    Remote service must have its token set in Joanie's settings `JOANIE_AUTHORIZED_API_TOKENS`
    """
    resource_link = request.query_params.get("resource_link")
    if resource_link is None:
        return Response(
            {"detail": "Query parameter `resource_link` is required."},
            status=400,
        )

    response = get_course_run_metrics(resource_link=resource_link)

    return JsonResponse(response, status=200)
